# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Saving a finalized SegWit transaction reads the inputs twice and the transaction once
# more for its ID. Every pass keeps the display updating, and 100% is left for the end.

from uio import BytesIO
from ustruct import pack

import progress
from psbt import psbtObject
from serializations import COutPoint, CTxIn, CTxOut, ser_compact_size

INPUTS = 5
P2WPKH_SCRIPT = b'\x00\x14' + (b'\x11' * 20)


class Input:
    is_segwit = True
    is_p2sh = False
    is_multisig = False
    tap_key_sig = None
    added_sig = (b'\x02' + b'\x22' * 32, b'\x30' * 71)


class Output:
    is_change = False
    witness_script = None


class PSBT:
    input_iter = psbtObject.input_iter
    output_iter = psbtObject.output_iter
    input_witness_iter = psbtObject.input_witness_iter

    def __init__(self, raw):
        self.fd = BytesIO(raw)
        self.txn = (0, len(raw))
        self.total_value_out = None


raw = pack('<i', 2) + ser_compact_size(INPUTS)
for idx in range(INPUTS):
    raw += CTxIn(COutPoint(idx + 1, 0)).serialize()
raw += ser_compact_size(1) + CTxOut(1000, P2WPKH_SCRIPT).serialize() + pack('<I', 0)

psbt = PSBT(raw)
psbtObject.parse_txn(psbt)
psbt.inputs = [Input() for _ in range(INPUTS)]
psbt.outputs = [Output()]

calls = []
originals = (progress.phase, progress.count, progress.step, progress.refresh)
try:
    progress.phase = lambda start, end: calls.append(('phase', start, end))
    progress.count = lambda total: calls.append(('count', total))
    progress.step = lambda: calls.append('step')
    progress.refresh = lambda: calls.append('refresh')
    psbtObject.finalize(psbt, BytesIO())
finally:
    progress.phase, progress.count, progress.step, progress.refresh = originals

phases = [call for call in calls if call[0] == 'phase']
assert phases == [('phase', 0, 45), ('phase', 45, 90), ('phase', 90, 99)], phases
cuts = [calls.index(phase) for phase in phases] + [len(calls)]
# The body and the witnesses each step once per input, and reading the transaction
# back for its ID steps once per block it counted beforehand.
assert calls[cuts[0]:cuts[1]].count('step') == INPUTS
assert calls[cuts[1]:cuts[2]].count('step') == INPUTS
blocks = [call[1] for call in calls[cuts[2]:cuts[3]] if call[0] == 'count']
assert len(blocks) == 1 and blocks[0] > 0, blocks
assert calls[cuts[2]:cuts[3]].count('step') == blocks[0]

return_value.write(b'OK')
