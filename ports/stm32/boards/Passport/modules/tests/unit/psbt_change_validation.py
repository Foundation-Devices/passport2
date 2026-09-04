# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Regression tests for PSBT change classification edge-cases.

from exceptions import FraudulentChangeOutput
from psbt import psbtObject, psbtOutputProxy
from serializations import CTxOut, hash160
from taproot import output_script
from ubinascii import a2b_base64
from uio import BytesIO


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
FIXTURE_XFP = 0xb869bcc3

# Derived from Downloads/simple test.psbt. The change output has BIP49 metadata
# and a redeem script for its supplied pubkey, but its transaction output uses
# an unrelated P2SH hash. This is the serialized form of the original exploit.
MALICIOUS_NESTED_P2SH_PSBT = (
    b'cHNidP8BAH4CAAAAAcXykgEKm0x7fbEPBIjbsrMVsBEofOcYRx3GowB5MPCqA'
    b'AAAAAAD9////AgQjaQgAAAAAF6kUIiIiIiIiIiIiIiIiIiIiIiIiIiKHECcAAAAA'
    b'AAAAACJRIPFdIHVbwHNjET7D4EGuu9dPK7uj6nVGcp3R7uELUEL6XEcCAE8BBDW'
    b'HzwR9QhRLgAAAApY2PuF86Li3yJI/vhLwk5RT+W1Ty8wXKDx5oooLtq76A6NIHq3'
    b'hdZr9YEI4SAYHC+VeWZDtvps7IqhAbrP6NcjoFMO8abgwAACAAQAAgAAAAIACAAC'
    b'AAAEBH2BKaQgAAAAAFgAU+XgaNYKLwIKFRUKWVhRJudara58BAwQBAAAAIgYDM4ay'
    b'sG88IJkJFt/MiEOuNY4TSEQM/+7fAq6THXtElGcYw7xpuFQAAIABAACAAAAAgAEAA'
    b'AAzAAAAAAEAFgAUbUQoa2KOGvP0RSxkIhJJHnPLK5oiAgP+2zYNOdR0oGJVANlG7'
    b'9sbTVTXOEs5jnE5Jej4ubq5RhjDvGm4MQAAgAEAAIAAAACAAQAAADQAAAAAAA=='
)

# Copied from Downloads/multi test.psbt. It carries a two-key BIP48 P2WSH
# change output and exercises parsing plus the multisig branch below.
MULTISIG_P2WSH_PSBT = (
    b'cHNidP8BAIkCAAAAAS/EqSBbfiU+7WIjuoOea/AkgaxM4s1b6s5gcTBsez7JAQAA'
    b'AAD9////Ar2fBQAAAAAAIgAgVeWwnnwasyzcZ9OkPne1JCzunSCZqWIhKXvAHxtH'
    b'qf4QJwAAAAAAACJRIPFdIHVbwHNjET7D4EGuu9dPK7uj6nVGcp3R7uELUEL6XEcC'
    b'AE8BBDWHzwR9QhRLgAAAApY2PuF86Li3yJI/vhLwk5RT+W1Ty8wXKDx5oooLtq76A'
    b'6NIHq3hdZr9YEI4SAYHC+VeWZDtvps7IqhAbrP6NcjoFMO8abgwAACAAQAAgAAAAI'
    b'ACAACATwEENYfPBOwQMsiAAAAC8y5GCAkNO45rMKWtKqzQFO90Cq2TIab1psvSQqV'
    b'UWx8CdpoLvP0no4RD5epSrL5sMutgWpAA1vsT2HvWkDv8YaUUnhicgDAAAIABAACA'
    b'AAAAgAIAAIAAAQErLMcFAAAAAAAiACB3W9tVXqP3G/HJzv5+dSF7HMYOTfL2C2XgGi'
    b'fqyvxVjwEDBAEAAAABBUdSIQIWA3WTnV674NNf3kcn5NzJQtNPiLwD6Xe3DvaF8u'
    b'qPGiED/AWPb/HtLOS+lDKZC+FdR9HIHkIwowHBhivTE3s0uEpSriIGA/wFj2/x7S'
    b'zkvpQymQvhXUfRyB5CMKMBwYYr0xN7NLhKHMO8abgwAACAAQAAgAAAAIACAACAAQ'
    b'AAAAIAAAAiBgIWA3WTnV674NNf3kcn5NzJQtNPiLwD6Xe3DvaF8uqPGhyeGJyAMAA'
    b'AgAEAAIAAAACAAgAAgAEAAAACAAAAAAEBR1IhA14ZHfXf3YgB81aOCoPxzCTKyXMm'
    b'iOiVPOGVjJhYXJL4IQPcDvtfqsnpn2PLU+atZK+HZdaBIc+0YBRZ83U6z/WHklKuI'
    b'gID3A77X6rJ6Z9jy1PmrWSvh2XWgSHPtGAUWfN1Os/1h5Icw7xpuDAAAIABAACAAA'
    b'AAgAIAAIABAAAAAwAAACICA14ZHfXf3YgB81aOCoPxzCTKyXMmiOiVPOGVjJhYXJL4'
    b'HJ4YnIAwAACAAQAAgAAAAIACAACAAQAAAAMAAAAAAA=='
)


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


def validate_must_fail(output, message='expected FraudulentChangeOutput', txo=None, my_xfp=MY_XFP):
    try:
        output.validate(0, txo or output._txo, my_xfp, None)
    except FraudulentChangeOutput:
        return

    raise RuntimeError(message)


def fixture_output(encoded_psbt, output_idx=0):
    psbt = psbtObject.read_psbt(BytesIO(a2b_base64(encoded_psbt)))
    psbt.my_xfp = FIXTURE_XFP
    for idx, txo in psbt.output_iter():
        if idx == output_idx:
            return psbt, psbt.outputs[idx], txo
    raise RuntimeError('fixture does not have the expected output')


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

# The serialized exploit must fail after normal PSBT parsing, not merely when
# validate() is called against a hand-built output proxy.
_, malicious_output, malicious_txo = fixture_output(MALICIOUS_NESTED_P2SH_PSBT)
validate_must_fail(malicious_output, 'serialized nested-P2SH exploit was accepted', malicious_txo,
                   FIXTURE_XFP)

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


class FixtureMultisig:
    def validate_script(self, _script, subpaths):
        assert len(subpaths) == 2


# Parsing a real BIP48 P2WSH fixture must still reach the multisig validation
# path and recognize matching change when the wallet policy accepts its script.
fixture_psbt, multisig_output, multisig_txo = fixture_output(MULTISIG_P2WSH_PSBT)
multisig_output.validate(0, multisig_txo, FIXTURE_XFP, FixtureMultisig())
assert multisig_output.is_change is True

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
