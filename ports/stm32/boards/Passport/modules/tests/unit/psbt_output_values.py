# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Test consensus bounds for output amounts in unsigned PSBT transactions.

from uio import BytesIO

from exceptions import FatalPSBTIssue
from psbt import psbtObject
from public_constants import MAX_MONEY
from serializations import CTxOut


P2WPKH_SCRIPT = b'\x00\x14' + (b'\x11' * 20)


class FakePSBT:
    def __init__(self, values):
        self.fd = BytesIO(b''.join(CTxOut(value, P2WPKH_SCRIPT).serialize() for value in values))
        self.vout_start = 0
        self.num_outputs = len(values)
        self.total_value_out = None


def read_outputs(values):
    psbt = FakePSBT(values)
    parsed = [tx_out.nValue for _, tx_out in psbtObject.output_iter(psbt)]
    return psbt, parsed


def assert_invalid(values):
    try:
        read_outputs(values)
    except FatalPSBTIssue:
        return
    raise AssertionError('Expected invalid output values to be rejected')


zero, parsed = read_outputs([0])
assert parsed == [0]
assert zero.total_value_out == 0

maximum, parsed = read_outputs([MAX_MONEY])
assert parsed == [MAX_MONEY]
assert maximum.total_value_out == MAX_MONEY

split_maximum, parsed = read_outputs([MAX_MONEY - 1, 1])
assert parsed == [MAX_MONEY - 1, 1]
assert split_maximum.total_value_out == MAX_MONEY

assert_invalid([-1])
assert_invalid([MAX_MONEY + 1])
assert_invalid([MAX_MONEY, 1])

return_value.write(b'OK')
