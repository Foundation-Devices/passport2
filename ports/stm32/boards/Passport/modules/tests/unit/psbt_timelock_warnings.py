# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Test timelock warnings on the device's Python.

from psbt import psbtObject
from psbt_display import format_utc_time, timelock_warnings
from serializations import CTxIn


class MockPSBT:
    def __init__(self, txn_version, lock_time, sequences):
        self.txn_version = txn_version
        self.lock_time = lock_time
        self.sequences = sequences
        self.warnings = []

    def input_iter(self):
        txin = CTxIn()
        for index, sequence in enumerate(self.sequences):
            txin.nSequence = sequence
            yield index, txin


assert format_utc_time(1798761600) == '2027-01-01 00:00'
assert format_utc_time(0xffffffff) == '2106-02-07 06:28'

# A wallet's usual anti-fee-sniping locktime isn't flagged.
normal = MockPSBT(2, 925000, [0xfffffffd, 0xfffffffd])
psbtObject.consider_timelocks(normal)
assert normal.warnings == []

locked = MockPSBT(2, 1798761600, [0xfffffffd, 144, (1 << 22) | 169])
psbtObject.consider_timelocks(locked)
assert [title for title, _ in locked.warnings] == ['Timelock', 'Relative Timelock']
assert '2027-01-01 00:00 UTC' in locked.warnings[0][1]
assert locked.warnings[1][1].endswith('Input 2: 144 blocks\nInput 3: about 1 day')
assert timelock_warnings(1, 0, [144]) == []

return_value.write(b'OK')
