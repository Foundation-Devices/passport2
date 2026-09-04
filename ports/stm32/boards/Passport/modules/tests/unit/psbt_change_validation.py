# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Regression tests for PSBT change classification edge-cases.

from exceptions import FraudulentChangeOutput
from psbt import psbtObject, psbtOutputProxy
from serializations import CTxOut, hash160
from taproot import output_script


MY_XFP = 0x12345678
PURPOSE_49 = 0x80000000 | 49
PURPOSE_84 = 0x80000000 | 84
PURPOSE_86 = 0x80000000 | 86
COIN_0 = 0x80000000
ACCOUNT_0 = 0x80000000
PUBKEY = b'\x02' + (b'\x11' * 32)
TAP_PUBKEY = b'\x33' * 32
PUBKEY_HASH = hash160(PUBKEY)
P2PK_SCRIPT = b'\x21' + PUBKEY + b'\xac'
REDEEM_SCRIPT = b'\x00\x14' + PUBKEY_HASH
GOOD_P2SH = b'\xa9\x14' + hash160(REDEEM_SCRIPT) + b'\x87'
BAD_P2SH = b'\xa9\x14' + (b'\x22' * 20) + b'\x87'
NATIVE_P2WPKH = b'\x00\x14' + PUBKEY_HASH
TAPROOT_SCRIPT = output_script(TAP_PUBKEY, None)
BIP49_SUBPATH = [MY_XFP, PURPOSE_49, COIN_0, ACCOUNT_0, 1, 7]
BIP84_INPUT_SUBPATH = [MY_XFP, PURPOSE_84, COIN_0, ACCOUNT_0, 0, 3]
BIP84_CHANGE_SUBPATH = [MY_XFP, PURPOSE_84, COIN_0, ACCOUNT_0, 1, 7]
BIP86_INPUT_SUBPATH = [MY_XFP, PURPOSE_86, COIN_0, ACCOUNT_0, 0, 9]
BIP86_CHANGE_SUBPATH = [MY_XFP, PURPOSE_86, COIN_0, ACCOUNT_0, 1, 8]
BIP84_SHORT_SUBPATH = [MY_XFP, PURPOSE_84]
BIP_UNKNOWN_SUBPATH = [MY_XFP, 0x80000000 | 123, COIN_0, ACCOUNT_0, 1, 7]


class FakeOutput:
    validate = psbtOutputProxy.validate

    def __init__(self, script_pubkey, subpaths=None, tap_subpaths=None, redeem_script=None):
        self.subpaths = subpaths
        self.tap_subpaths = tap_subpaths
        self.redeem_script = redeem_script
        self.witness_script = None
        self.is_change = False
        self._txo = CTxOut(0, script_pubkey)

    def parse_subpaths(self, my_xfp):
        assert my_xfp == MY_XFP
        return 1

    def get(self, value):
        return value


def must_fail(script_pubkey):
    try:
        FakeOutput(script_pubkey,
                   subpaths={PUBKEY: BIP49_SUBPATH},
                   redeem_script=REDEEM_SCRIPT).validate(0, CTxOut(0, script_pubkey), MY_XFP, None)
    except FraudulentChangeOutput:
        return

    raise RuntimeError('expected FraudulentChangeOutput')


def validate_must_fail(output, message='expected FraudulentChangeOutput'):
    try:
        output.validate(0, output._txo, MY_XFP, None)
    except FraudulentChangeOutput:
        return

    raise RuntimeError(message)


class FakeInput:
    def __init__(self, subpaths=None, tap_subpaths=None, required_key=None):
        self.subpaths = subpaths or {}
        self.tap_subpaths = tap_subpaths or {}
        self.required_key = required_key
        self.fully_signed = False


class FakePsbt:
    consider_dangerous_change = psbtObject.consider_dangerous_change

    def __init__(self, inputs, outputs):
        self.inputs = inputs
        self.outputs = outputs
        self.warnings = []


def assert_no_mixed_change_warning(outputs):
    mixed_inputs = [
        FakeInput(subpaths={PUBKEY: BIP84_INPUT_SUBPATH}, required_key=PUBKEY),
        FakeInput(tap_subpaths={TAP_PUBKEY: (BIP86_INPUT_SUBPATH, [])}, required_key=TAP_PUBKEY),
    ]
    fake_psbt = FakePsbt(mixed_inputs, outputs)
    fake_psbt.consider_dangerous_change(MY_XFP)
    assert fake_psbt.warnings == []


valid = FakeOutput(GOOD_P2SH,
                   subpaths={PUBKEY: BIP49_SUBPATH},
                   redeem_script=REDEEM_SCRIPT)
valid.validate(0, CTxOut(0, GOOD_P2SH), MY_XFP, None)
assert valid.is_change is True

must_fail(BAD_P2SH)
must_fail(NATIVE_P2WPKH)

# Raw P2PK outputs and unknown derivations remain visible rather than being
# treated as change or aborting a signing operation.
raw_p2pk = FakeOutput(P2PK_SCRIPT, subpaths={PUBKEY: BIP84_CHANGE_SUBPATH})
raw_p2pk.validate(0, raw_p2pk._txo, MY_XFP, None)
assert raw_p2pk.is_change is False

# Taproot metadata is only valid for a BIP86-derived P2TR output.
validate_must_fail(FakeOutput(TAPROOT_SCRIPT,
                              tap_subpaths={TAP_PUBKEY: (BIP84_CHANGE_SUBPATH, [])}))

# A single-sig path without a recognized full account derivation is not safe to
# classify as change, but should not prevent signing.
for path in (BIP84_SHORT_SUBPATH, BIP_UNKNOWN_SUBPATH):
    unsupported_path = FakeOutput(NATIVE_P2WPKH, subpaths={PUBKEY: path})
    unsupported_path.validate(0, unsupported_path._txo, MY_XFP, None)
    assert unsupported_path.is_change is False

valid_mixed_segwit_change = FakeOutput(NATIVE_P2WPKH, subpaths={PUBKEY: BIP84_CHANGE_SUBPATH})
valid_mixed_segwit_change.validate(0, CTxOut(0, NATIVE_P2WPKH), MY_XFP, None)
assert valid_mixed_segwit_change.is_change is True
assert_no_mixed_change_warning([valid_mixed_segwit_change])

valid_mixed_taproot_change = FakeOutput(TAPROOT_SCRIPT,
                                        tap_subpaths={TAP_PUBKEY: (BIP86_CHANGE_SUBPATH, [])})
valid_mixed_taproot_change.validate(0, CTxOut(0, TAPROOT_SCRIPT), MY_XFP, None)
assert valid_mixed_taproot_change.is_change is True
assert_no_mixed_change_warning([valid_mixed_taproot_change])

wrong_tap_metadata_for_segwit = FakeOutput(NATIVE_P2WPKH,
                                           tap_subpaths={TAP_PUBKEY: (BIP86_CHANGE_SUBPATH, [])})
try:
    wrong_tap_metadata_for_segwit.validate(0, CTxOut(0, NATIVE_P2WPKH), MY_XFP, None)
except FraudulentChangeOutput:
    pass
else:
    raise RuntimeError('expected FraudulentChangeOutput for segwit output with taproot metadata')

wrong_segwit_metadata_for_taproot = FakeOutput(TAPROOT_SCRIPT, subpaths={PUBKEY: BIP84_CHANGE_SUBPATH})
try:
    wrong_segwit_metadata_for_taproot.validate(0, CTxOut(0, TAPROOT_SCRIPT), MY_XFP, None)
except FraudulentChangeOutput:
    pass
else:
    raise RuntimeError('expected FraudulentChangeOutput for taproot output with segwit metadata')

return_value.write(b'OK')
