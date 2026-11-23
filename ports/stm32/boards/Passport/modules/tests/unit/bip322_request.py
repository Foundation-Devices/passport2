# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Route a BIP-322 request sent as a PSBT through the message flow, its validation and its signing, with a
# stand-in keystore. tests/unit/bip322.py checks the request parsing and the signature itself.

import uasyncio as asyncio
from ubinascii import unhexlify as a2b_hex
from ustruct import pack

import common
import stash
import flows.sign_electrum_message_flow as electrum
from bip322 import INVALID_REQUEST, TAPROOT_ONLY, create_virtual_transactions
from data_codecs.qr_type import QRType
from foundation import secp256k1, ur
from public_constants import AF_P2TR, AF_P2WPKH
from serializations import SIGHASH_ALL, ser_string
from taproot import output_script
from tasks.sign_text_file_task import sign_text_file_task
from tasks.validate_bip322_request_task import validate_bip322_request_task
from utils import swab32


class MemorySettings:
    def __init__(self):
        self.values = {}

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value):
        self.values[key] = value


if common.settings is None:
    common.settings = MemorySettings()

HARDENED = 0x80000000
XFP = 0x78563412
PATH = [86 | HARDENED, 1 | HARDENED, HARDENED, 0, 0]
SUBPATH = "m/86'/1'/0'/0/0"
ADDRESS = 'tb1p-address'
PRIVATE_KEY = a2b_hex('f805d22c9379f60b87770c8358c8fc2310b3e65d1c4555a51f58c912862b385b')
INTERNAL_PUBKEY = secp256k1.public_key_schnorr(PRIVATE_KEY)
SCRIPT = output_script(INTERNAL_PUBKEY, None)
MESSAGE = 'Proof of reserves for tb1p'


def request_psbt(message=MESSAGE.encode(), path=PATH, script=SCRIPT, derivation_value=None):
    _, to_sign = create_virtual_transactions(message, script)
    if derivation_value is None:
        derivation_value = b'\x00' + pack('<%dI' % (1 + len(path)), XFP, *path)
    entries = ((b'\x00', to_sign), (b'\x09', message), None,
               (b'\x01', pack('<q', 0) + ser_string(script)),
               (b'\x03', pack('<I', SIGHASH_ALL)),
               (b'\x16' + INTERNAL_PUBKEY, derivation_value),
               (b'\x17', INTERNAL_PUBKEY), None, None)
    out = b'psbt\xff'
    for entry in entries:
        out += b'\x00' if entry is None else ser_string(entry[0]) + ser_string(entry[1])
    return out


class KeyNode:
    public_key_bytes = b'\x02' + INTERNAL_PUBKEY

    def public_key(self):
        return self.public_key_bytes

    def private_key(self):
        return bytearray(PRIVATE_KEY)


class KeyValues:
    derived = []

    def __enter__(self):
        self.chain = self
        return self

    def __exit__(self, *args):
        pass

    def derive_path(self, path):
        self.derived.append(path)
        return KeyNode()

    def address(self, node, addr_type):
        return ADDRESS

    def register(self, value):
        pass


async def validate(psbt):
    results = []

    async def on_done(value, error):
        results.append((value, error))

    await validate_bip322_request_task(on_done, psbt)
    assert len(results) == 1
    return results[0]


async def sign(request, addr_fmt=AF_P2TR):
    results = []

    async def on_done(signature, address, error):
        results.append((signature, address, error))

    await sign_text_file_task(on_done, MESSAGE, SUBPATH, addr_fmt, ADDRESS, request)
    assert len(results) == 1
    return results[0]


async def run_task_tests():
    # A request from this wallet for a Taproot path is shown as text with its path.
    psbt = request_psbt()
    KeyValues.derived = []
    value, error = await validate(psbt)
    assert error is None, error
    message, subpath, request = value
    assert message == MESSAGE
    assert subpath == SUBPATH
    assert KeyValues.derived == [SUBPATH]

    # Fingerprints are matched in either byte order, as when signing a transaction.
    common.settings.set('xfp', swab32(XFP))
    assert (await validate(psbt))[1] is None
    common.settings.set('xfp', 0x01020304)
    assert (await validate(psbt))[1] == 'This message request is for a different wallet.'
    common.settings.set('xfp', XFP)

    # The address shown comes from the path, so the path must be a Taproot one.
    value, error = await validate(request_psbt(path=[84 | HARDENED, 1 | HARDENED, HARDENED, 0, 0]))
    assert error == TAPROOT_ONLY

    # The text checks are the ones a message scanned as text gets.
    for message in (b'visible\x00hidden', b'visible\x1bhidden', b'caf\xc3\xa9', b'\xff\xfe'):
        value, error = await validate(request_psbt(message=message))
        assert value is None
        assert error is not None

    # A key at that path must own the address in the request.
    KeyNode.public_key_bytes = b'\x02' + secp256k1.public_key_schnorr(a2b_hex('01' * 32))
    try:
        value, error = await validate(psbt)
        assert error == 'The address in this request does not match its derivation path.'
    finally:
        KeyNode.public_key_bytes = b'\x02' + INTERNAL_PUBKEY

    assert (await validate(b'psbt\xff'))[1] == INVALID_REQUEST
    for derivation_value in (b'', b'\x00'):
        assert await validate(request_psbt(derivation_value=derivation_value)) == (None, INVALID_REQUEST)

    # Signing returns the request's PSBT with the key-path signature added to its input.
    signed, address, error = await sign(request)
    assert error is None, error
    assert address == ADDRESS
    offset = request.signature_offset
    assert signed[:offset] == psbt[:offset]
    assert signed[offset:offset + 3] == b'\x01\x13\x41'
    assert signed[offset + 3 + 64] == SIGHASH_ALL
    assert signed[offset + 3 + 65:] == psbt[offset:]

    # A request is only signed with the Taproot key it names.
    assert (await sign(request, addr_fmt=AF_P2WPKH))[2] is not None


class MockScanQRFlow:
    result = None
    kwargs = None

    def __init__(self, **kwargs):
        MockScanQRFlow.kwargs = kwargs

    async def run(self):
        return MockScanQRFlow.result


class MockShowQRPage:
    shown = []

    def __init__(self, qr_type, qr_data, right_micron):
        self.shown.append((qr_type, qr_data))

    async def show(self):
        return True


class MockFlow:
    psbt = None
    bip322_request = None
    validate_message = 'validate-message'
    validate_bip322_request = 'validate-bip322-request'
    show_message = 'show-message'
    show_signed = 'show-signed'

    def goto(self, state, **kwargs):
        self.next_state = state

    def set_result(self, result):
        self.result = result


async def run_flow_tests():
    psbt = request_psbt()

    # A PSBT scanned in the message flow goes to BIP-322 validation; text still goes to message validation.
    MockScanQRFlow.result = ur.new_psbt(psbt)
    flow = MockFlow()
    await electrum.SignElectrumMessageFlow.scan_message(flow)
    assert QRType.UR2 in MockScanQRFlow.kwargs['qr_types']
    assert MockScanQRFlow.kwargs['ur_types'] == [ur.Value.PSBT]
    assert flow.next_state == flow.validate_bip322_request
    assert flow.psbt == psbt

    MockScanQRFlow.result = 'signmessage {} ascii:{}'.format(SUBPATH, MESSAGE)
    flow = MockFlow()
    await electrum.SignElectrumMessageFlow.scan_message(flow)
    assert flow.next_state == flow.validate_message
    assert flow.message == MockScanQRFlow.result

    # Validation hands the review the message and path, and keeps the request for signing.
    flow = MockFlow()
    flow.psbt = psbt
    await electrum.SignElectrumMessageFlow.validate_bip322_request(flow)
    assert flow.next_state == flow.show_message
    assert flow.message == MESSAGE
    assert flow.subpath == SUBPATH
    assert flow.bip322_request.message == MESSAGE.encode()
    assert flow.psbt is None

    # Signing passes the request along, and the result goes back as a PSBT.
    flow.addr_format = AF_P2TR
    flow.address = ADDRESS
    await electrum.SignElectrumMessageFlow.do_sign(flow)
    assert flow.next_state == flow.show_signed
    MockShowQRPage.shown = []
    await electrum.SignElectrumMessageFlow.show_signed(flow)
    ((qr_type, qr_data),) = MockShowQRPage.shown
    assert qr_type == QRType.UR2
    assert qr_data.ur_type() == ur.Value.PSBT
    assert bytes(qr_data.unwrap_psbt()) == flow.signature

    # A text signature is still shown as plain text.
    flow = MockFlow()
    flow.signature = 'H1234='
    MockShowQRPage.shown = []
    await electrum.SignElectrumMessageFlow.show_signed(flow)
    assert MockShowQRPage.shown == [(QRType.QR, 'H1234=')]


async def run_spinner(label, task, args):
    results = []

    async def on_done(*values):
        results.append(values)

    await task(on_done, *args)
    assert len(results) == 1
    return results[0]


async def run_tests():
    original_xfp = common.settings.get('xfp')
    original_sensitive_values = stash.SensitiveValues
    original_scan = electrum.ScanQRFlow
    original_show = electrum.ShowQRPage
    original_spinner = electrum.spinner_task
    try:
        common.settings.set('xfp', XFP)
        stash.SensitiveValues = KeyValues
        electrum.ScanQRFlow = MockScanQRFlow
        electrum.ShowQRPage = MockShowQRPage
        electrum.spinner_task = run_spinner
        await run_task_tests()
        await run_flow_tests()
    finally:
        common.settings.set('xfp', original_xfp)
        stash.SensitiveValues = original_sensitive_values
        electrum.ScanQRFlow = original_scan
        electrum.ShowQRPage = original_show
        electrum.spinner_task = original_spinner


asyncio.run(run_tests())
return_value.write(b'OK')
