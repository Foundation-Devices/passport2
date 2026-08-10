# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Test PSBT input-value validation and fee review rendering.

from uio import BytesIO
from ustruct import pack

from exceptions import FatalPSBTIssue
from flows.sign_psbt_common_flow import SignPsbtCommonFlow
from psbt import psbtInputProxy, psbtObject
from public_constants import (
    PSBT_IN_NON_WITNESS_UTXO,
    PSBT_IN_REDEEM_SCRIPT,
    PSBT_IN_WITNESS_UTXO,
)
from serializations import CTxOut, hash160, ser_compact_size


P2WPKH_SCRIPT = b'\x00\x14' + (b'\x11' * 20)
P2PKH_SCRIPT = b'\x76\xa9\x14' + (b'\x22' * 20) + b'\x88\xac'
DUMMY_PUBKEY = b'\x02' + (b'\x55' * 32)


def psbt_field(key_type, value):
    return b'\x01' + bytes([key_type]) + ser_compact_size(len(value)) + value


def previous_tx(txout):
    txin = (b'\x00' * 32) + pack('<I', 0) + b'\x00' + pack('<I', 0xffffffff)
    return pack('<i', 2) + b'\x01' + txin + b'\x01' + txout.serialize() + pack('<I', 0)


def make_input(witness_txout, non_witness_txout=None, redeem_script=None):
    data = b''
    if non_witness_txout:
        data += psbt_field(PSBT_IN_NON_WITNESS_UTXO, previous_tx(non_witness_txout))
    data += psbt_field(PSBT_IN_WITNESS_UTXO, witness_txout.serialize())
    if redeem_script:
        data += psbt_field(PSBT_IN_REDEEM_SCRIPT, redeem_script)
    return psbtInputProxy(BytesIO(data + b'\x00'), 0)


def assert_raises(exc_type, callback):
    try:
        callback()
    except exc_type:
        return
    raise AssertionError('Expected {}'.format(exc_type))


matching = CTxOut(1000, P2WPKH_SCRIPT)
loaded = make_input(matching, matching).get_utxo(0)
assert loaded.nValue == matching.nValue
assert loaded.scriptPubKey == matching.scriptPubKey

amount_mismatch = make_input(CTxOut(999, P2WPKH_SCRIPT), matching)
assert_raises(AssertionError, lambda: amount_mismatch.get_utxo(0))

script_mismatch = make_input(CTxOut(1000, b'\x00\x14' + (b'\x33' * 20)), matching)
assert_raises(AssertionError, lambda: script_mismatch.get_utxo(0))

legacy = make_input(CTxOut(1000, P2PKH_SCRIPT))
legacy.subpaths[DUMMY_PUBKEY] = []
assert_raises(FatalPSBTIssue, lambda: legacy.determine_my_signing_key(0, CTxOut(1000, P2PKH_SCRIPT), 0, None))

native_segwit = make_input(CTxOut(1000, P2WPKH_SCRIPT))
native_segwit.subpaths[DUMMY_PUBKEY] = []
native_segwit.determine_my_signing_key(0, CTxOut(1000, P2WPKH_SCRIPT), 0, None)
assert native_segwit.is_segwit

wrapped_program = b'\x00\x14' + (b'\x44' * 20)
wrapped_script = b'\xa9\x14' + hash160(wrapped_program) + b'\x87'
wrapped_segwit = make_input(CTxOut(1000, wrapped_script), redeem_script=wrapped_program)
wrapped_segwit.subpaths[DUMMY_PUBKEY] = []
wrapped_segwit.determine_my_signing_key(0, CTxOut(1000, wrapped_script), 0, None)
assert wrapped_segwit.is_segwit


class FakeInput:
    def __init__(self, owned):
        self.owned = owned
        self.fully_signed = False
        self.witness_utxo = True
        self.utxo = None
        self.required_key = None
        self.num_our_keys = 1 if owned else 0
        self.is_segwit = False
        self.subpaths = {}
        self.tap_subpaths = {}

    def has_utxo(self):
        return True

    def get_utxo(self, _idx):
        return CTxOut(2000, P2WPKH_SCRIPT)

    def determine_my_signing_key(self, _idx, utxo, _xfp, _psbt):
        self.amount = utxo.nValue
        self.required_key = b'key' if self.owned else None


class FakePrevout:
    n = 0


class FakeTxIn:
    prevout = FakePrevout()


class FakeInputPSBT:
    def __init__(self, owned):
        self.inputs = [FakeInput(owned)]
        self.my_xfp = 0
        self.total_value_in = None
        self.fee_is_verified = True
        self.presigned_inputs = set()
        self.num_inputs = 1
        self.warnings = []

    def input_iter(self):
        yield 0, FakeTxIn()


external_input_psbt = FakeInputPSBT(False)
psbtObject.consider_inputs(external_input_psbt)
assert not external_input_psbt.fee_is_verified

owned_input_psbt = FakeInputPSBT(True)
psbtObject.consider_inputs(owned_input_psbt)
assert owned_input_psbt.fee_is_verified


class FakeOutputProxy:
    is_change = False

    def validate(self, _idx, _txout, _xfp, _active_multisig):
        pass


class FakeOutputPSBT:
    def __init__(self, fee_is_verified):
        self.outputs = [FakeOutputProxy()]
        self.total_value_out = 1000
        self.total_value_in = 5000
        self.fee_is_verified = fee_is_verified
        self.self_send = False
        self.warnings = []
        self.my_xfp = 0
        self.active_multisig = None

    def output_iter(self):
        yield 0, CTxOut(self.total_value_out, P2WPKH_SCRIPT)

    def calculate_fee(self):
        return self.total_value_in - self.total_value_out

    def consider_dangerous_change(self, _xfp):
        pass


unverified_fee_psbt = FakeOutputPSBT(False)
psbtObject.consider_outputs(unverified_fee_psbt)
assert unverified_fee_psbt.warnings[0][0] == 'Unverified Fee'
assert all(label not in {'Big Fee', 'Huge Fee'} for label, _text in unverified_fee_psbt.warnings)

verified_fee_psbt = FakeOutputPSBT(True)
psbtObject.consider_outputs(verified_fee_psbt)
assert verified_fee_psbt.warnings[0][0] == 'Huge Fee'


class FakeChain:
    def render_value(self, value):
        return str(value), 'sats'


class FakeFlow:
    chain = FakeChain()

    def __init__(self, psbt):
        self.psbt = psbt


review = SignPsbtCommonFlow.render_warnings(FakeFlow(unverified_fee_psbt))
assert 'Unverified' in review
assert '4000 sats' not in review

review = SignPsbtCommonFlow.render_warnings(FakeFlow(verified_fee_psbt))
assert '4000 sats' in review

return_value.write(b'OK')
