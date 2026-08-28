# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Test consensus bounds for input and output amounts in unsigned PSBT transactions.

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


class FakePrevout:
    n = 0


class FakeTxIn:
    prevout = FakePrevout()


class FakeInput:
    def __init__(self, value):
        self.value = value
        self.fully_signed = False
        self.num_our_keys = 1
        self.required_key = b'key'
        self.is_segwit = False
        self.witness_utxo = False

    def has_utxo(self):
        return True

    def get_utxo(self, _idx):
        return CTxOut(self.value, P2WPKH_SCRIPT)

    def determine_my_signing_key(self, _idx, _utxo, _xfp, _psbt):
        pass


class FakeInputPSBT:
    def __init__(self, values):
        self.inputs = [FakeInput(value) for value in values]
        self.my_xfp = 0
        self.total_value_in = None
        self.fee_is_verified = True
        self.presigned_inputs = set()
        self.num_inputs = len(values)
        self.warnings = []

    def input_iter(self):
        for idx in range(self.num_inputs):
            yield idx, FakeTxIn()


def read_outputs(values):
    psbt = FakePSBT(values)
    parsed = [tx_out.nValue for _, tx_out in psbtObject.output_iter(psbt)]
    return psbt, parsed


def read_inputs(values):
    psbt = FakeInputPSBT(values)
    psbtObject.consider_inputs(psbt)
    return psbt


def assert_invalid_outputs(values, invalid_idx):
    psbt = FakePSBT(values)
    try:
        list(psbtObject.output_iter(psbt))
    except FatalPSBTIssue as exc:
        assert '#%d' % invalid_idx in str(exc)
        assert psbt.total_value_out is None
        return
    raise AssertionError('Expected invalid output values to be rejected')


def assert_invalid_inputs(values, invalid_idx):
    psbt = FakeInputPSBT(values)
    try:
        psbtObject.consider_inputs(psbt)
    except FatalPSBTIssue as exc:
        assert '#%d' % invalid_idx in str(exc)
        assert psbt.total_value_in is None
        return
    raise AssertionError('Expected invalid input values to be rejected')


zero, parsed = read_outputs([0])
assert parsed == [0]
assert zero.total_value_out == 0

maximum, parsed = read_outputs([MAX_MONEY])
assert parsed == [MAX_MONEY]
assert maximum.total_value_out == MAX_MONEY

split_maximum, parsed = read_outputs([MAX_MONEY - 1, 1])
assert parsed == [MAX_MONEY - 1, 1]
assert split_maximum.total_value_out == MAX_MONEY

assert_invalid_outputs([-1], 0)
assert_invalid_outputs([MAX_MONEY + 1], 0)
assert_invalid_outputs([1, -(1 << 63)], 1)
assert_invalid_outputs([MAX_MONEY, 1], 1)

one_input = read_inputs([1])
assert one_input.total_value_in == 1

maximum_input = read_inputs([MAX_MONEY])
assert maximum_input.total_value_in == MAX_MONEY

split_maximum_inputs = read_inputs([MAX_MONEY - 1, 1])
assert split_maximum_inputs.total_value_in == MAX_MONEY

assert_invalid_inputs([0], 0)
assert_invalid_inputs([-1], 0)
assert_invalid_inputs([MAX_MONEY + 1], 0)
assert_invalid_inputs([1, 1 << 62], 1)
assert_invalid_inputs([MAX_MONEY, 1], 1)

return_value.write(b'OK')
