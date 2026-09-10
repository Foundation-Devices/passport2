# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Regression tests for PSBT change classification edge-cases.

from exceptions import FraudulentChangeOutput
from psbt import psbtObject, psbtOutputProxy
from serializations import CTxOut, hash160
from taproot import output_script
import trezorcrypto


MY_XFP = 0x12345678
PURPOSE_49 = 0x80000000 | 49
PURPOSE_48 = 0x80000000 | 48
PURPOSE_84 = 0x80000000 | 84
PURPOSE_86 = 0x80000000 | 86
COIN_0 = 0x80000000
ACCOUNT_0 = 0x80000000
PUBKEY = b'\x02' + (b'\x11' * 32)
TAP_PUBKEY = b'\x33' * 32
PUBKEY_HASH = hash160(PUBKEY)
MULTISIG_SCRIPT = b'\x51\x21' + PUBKEY + b'\x51\xae'
MULTISIG_SCRIPT_HASH = trezorcrypto.sha256(MULTISIG_SCRIPT).digest()
P2PK_SCRIPT = b'\x21' + PUBKEY + b'\xac'
REDEEM_SCRIPT = b'\x00\x14' + PUBKEY_HASH
GOOD_P2SH = b'\xa9\x14' + hash160(REDEEM_SCRIPT) + b'\x87'
BAD_P2SH = b'\xa9\x14' + (b'\x22' * 20) + b'\x87'
NATIVE_P2WPKH = b'\x00\x14' + PUBKEY_HASH
LEGACY_P2SH = b'\xa9\x14' + hash160(MULTISIG_SCRIPT) + b'\x87'
P2WSH_REDEEM_SCRIPT = b'\x00\x20' + MULTISIG_SCRIPT_HASH
NESTED_P2WSH = b'\xa9\x14' + hash160(P2WSH_REDEEM_SCRIPT) + b'\x87'
NATIVE_P2WSH = b'\x00\x20' + MULTISIG_SCRIPT_HASH
TAPROOT_SCRIPT = output_script(TAP_PUBKEY, None)
BIP49_SUBPATH = [MY_XFP, PURPOSE_49, COIN_0, ACCOUNT_0, 1, 7]
BIP48_SUBPATH = [MY_XFP, PURPOSE_48, COIN_0, ACCOUNT_0, 0x80000000 | 2, 1, 7]
BIP84_INPUT_SUBPATH = [MY_XFP, PURPOSE_84, COIN_0, ACCOUNT_0, 0, 3]
BIP84_CHANGE_SUBPATH = [MY_XFP, PURPOSE_84, COIN_0, ACCOUNT_0, 1, 7]
BIP86_INPUT_SUBPATH = [MY_XFP, PURPOSE_86, COIN_0, ACCOUNT_0, 0, 9]
BIP86_CHANGE_SUBPATH = [MY_XFP, PURPOSE_86, COIN_0, ACCOUNT_0, 1, 8]
BIP84_SHORT_SUBPATH = [MY_XFP, PURPOSE_84]
BIP_UNKNOWN_SUBPATH = [MY_XFP, 0x80000000 | 123, COIN_0, ACCOUNT_0, 1, 7]


class FakeOutput:
    validate = psbtOutputProxy.validate

    def __init__(self, script_pubkey, subpaths=None, tap_subpaths=None, redeem_script=None,
                 witness_script=None):
        self.subpaths = subpaths
        self.tap_subpaths = tap_subpaths
        self.redeem_script = redeem_script
        self.witness_script = witness_script
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


def validate_must_fail(output, message='expected FraudulentChangeOutput', active_multisig=None):
    try:
        output.validate(0, output._txo, MY_XFP, active_multisig)
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


class OneOfOneMultisig:
    def validate_script(self, script, subpaths):
        assert script == MULTISIG_SCRIPT
        assert subpaths == {PUBKEY: BIP48_SUBPATH}


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


# BIP48 1-of-1 script wallets have one of our derivation entries, but still
# require registered-wallet script validation rather than the single-sig path.
for script_pubkey, redeem_script, witness_script in (
        (LEGACY_P2SH, MULTISIG_SCRIPT, None),
        (NESTED_P2WSH, P2WSH_REDEEM_SCRIPT, MULTISIG_SCRIPT),
        (NATIVE_P2WSH, None, MULTISIG_SCRIPT)):
    one_of_one_change = FakeOutput(script_pubkey,
                                   subpaths={PUBKEY: BIP48_SUBPATH},
                                   redeem_script=redeem_script,
                                   witness_script=witness_script)
    one_of_one_change.validate(0, one_of_one_change._txo, MY_XFP, OneOfOneMultisig())
    assert one_of_one_change.is_change is True


# A script-wallet path must not use the single-sig nested-P2WPKH branch.
# Reject it as fraud rather than hashing the absent single-sig public key.
for purpose in (45, 48):
    script_wallet_path = list(BIP48_SUBPATH)
    script_wallet_path[1] = 0x80000000 | purpose
    validate_must_fail(FakeOutput(GOOD_P2SH,
                                  subpaths={PUBKEY: script_wallet_path},
                                  redeem_script=REDEEM_SCRIPT),
                       active_multisig=OneOfOneMultisig())


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
validate_must_fail(wrong_tap_metadata_for_segwit,
                   'expected FraudulentChangeOutput for segwit output with taproot metadata')

wrong_segwit_metadata_for_taproot = FakeOutput(TAPROOT_SCRIPT, subpaths={PUBKEY: BIP84_CHANGE_SUBPATH})
validate_must_fail(wrong_segwit_metadata_for_taproot,
                   'expected FraudulentChangeOutput for taproot output with segwit metadata')

return_value.write(b'OK')
