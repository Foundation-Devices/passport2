# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Regression tests for PSBT change classification edge-cases.

from exceptions import FraudulentChangeOutput
from psbt import psbtOutputProxy
from serializations import CTxOut, hash160


MY_XFP = 0x12345678
PURPOSE_49 = 0x80000000 | 49
COIN_0 = 0x80000000
ACCOUNT_0 = 0x80000000
PUBKEY = b'\x02' + (b'\x11' * 32)
PUBKEY_HASH = hash160(PUBKEY)
REDEEM_SCRIPT = b'\x00\x14' + PUBKEY_HASH
GOOD_P2SH = b'\xa9\x14' + hash160(REDEEM_SCRIPT) + b'\x87'
BAD_P2SH = b'\xa9\x14' + (b'\x22' * 20) + b'\x87'
NATIVE_P2WPKH = b'\x00\x14' + PUBKEY_HASH
SUBPATH = [MY_XFP, PURPOSE_49, COIN_0, ACCOUNT_0, 1, 7]


class FakeOutput:
    validate = psbtOutputProxy.validate

    def __init__(self, script_pubkey):
        self.subpaths = {PUBKEY: SUBPATH}
        self.tap_subpaths = None
        self.redeem_script = REDEEM_SCRIPT
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
        FakeOutput(script_pubkey).validate(0, CTxOut(0, script_pubkey), MY_XFP, None)
    except FraudulentChangeOutput:
        return

    raise RuntimeError('expected FraudulentChangeOutput')


valid = FakeOutput(GOOD_P2SH)
valid.validate(0, CTxOut(0, GOOD_P2SH), MY_XFP, None)
assert valid.is_change is True

must_fail(BAD_P2SH)
must_fail(NATIVE_P2WPKH)

return_value.write(b'OK')
