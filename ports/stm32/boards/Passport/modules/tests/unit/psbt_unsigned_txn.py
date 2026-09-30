# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# BIP-174 requires the unsigned transaction inside a PSBT to be serialized without
# witness data. Passport rejects anything else, so it never has witness data of its
# own to preserve and always fills the witness area itself when finalizing.

from uio import BytesIO
from ustruct import pack

from exceptions import FatalPSBTIssue
from psbt import psbtObject
from serializations import COutPoint, CTxIn, CTxInWitness, CTxOut, ser_compact_size

P2WPKH_SCRIPT = b'\x00\x14' + (b'\x11' * 20)
OUTPUT_VALUE = 1000


class MockPSBT:
    '''Just enough of a psbtObject for parse_txn() and the iterators to work on.'''

    def __init__(self, raw):
        self.fd = BytesIO(raw)
        self.txn = (0, len(raw))
        self.total_value_out = None


def ser_unsigned_txn(num_in=1, num_out=1, version=2, witness=False):
    body = pack('<i', version)

    if witness:
        body += b'\x00\x01'

    body += ser_compact_size(num_in)
    for idx in range(num_in):
        body += CTxIn(COutPoint(idx + 1, idx)).serialize()

    body += ser_compact_size(num_out)
    for _ in range(num_out):
        body += CTxOut(OUTPUT_VALUE, P2WPKH_SCRIPT).serialize()

    if witness:
        for _ in range(num_in):
            body += CTxInWitness().serialize()

    body += pack('<I', 0)
    return body


def must_raise(exc_type, call):
    try:
        call()
    except exc_type:
        return

    raise RuntimeError('expected {}'.format(exc_type.__name__))


# A compliant unsigned transaction parses, and the positions it records let the
# input and output iterators walk it.
psbt = MockPSBT(ser_unsigned_txn(num_in=2, num_out=3))
psbtObject.parse_txn(psbt)

assert psbt.txn_version == 2
assert psbt.num_inputs == 2
assert psbt.num_outputs == 3
assert psbt.lock_time == 0

assert [idx for idx, _ in psbtObject.input_iter(psbt)] == [0, 1]
assert [txo.nValue for _, txo in psbtObject.output_iter(psbt)] == [OUTPUT_VALUE] * 3

# Witness serialization is rejected with a message a caller can show, rather than
# the bare ValueError('CTxInWitness') that _skip_n_objs() used to raise once the
# parser reached the witness area.
must_raise(FatalPSBTIssue,
           lambda: psbtObject.parse_txn(MockPSBT(ser_unsigned_txn(witness=True))))

# A zero input count is indistinguishable from the segwit marker, so it is caught on
# that path rather than by the 'no ins?' assertion. Either way it is rejected.
must_raise(FatalPSBTIssue,
           lambda: psbtObject.parse_txn(MockPSBT(ser_unsigned_txn(num_in=0))))

# Version checking is unaffected.
must_raise(AssertionError,
           lambda: psbtObject.parse_txn(MockPSBT(ser_unsigned_txn(version=3))))

# finalize() fills the witness area itself, so every input gets a fresh empty
# witness it can assign a stack to.
witnesses = list(psbtObject.input_witness_iter(psbt))
assert [idx for idx, _ in witnesses] == [0, 1]
assert all(wit.scriptWitness.stack == [] for _, wit in witnesses)
assert witnesses[0][1] is not witnesses[1][1]

return_value.write(b'OK')
