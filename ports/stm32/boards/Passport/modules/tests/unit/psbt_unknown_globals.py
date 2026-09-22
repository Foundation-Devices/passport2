# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Unknown and proprietary global fields must survive PSBT parsing and serialization.

from uio import BytesIO
from ustruct import pack

import common
from psbt import psbtObject
from serializations import CTxOut, ser_string


# Unsigned transaction with one input and one output, followed by empty PSBT maps.
txin = (b'\x11' * 32) + pack('<I', 0) + b'\x00' + pack('<I', 0xffffffff)
txout = CTxOut(1000, b'\x00\x14' + b'\x22' * 20)
txn = pack('<i', 2) + b'\x01' + txin + b'\x01' + txout.serialize() + pack('<I', 0)
unknowns = (
    (b'\x50extra', b'unknown value'),
    (b'\xfc\x04test\x00extra', b'proprietary value'),
)
data = b'psbt\xff' + ser_string(b'\x00') + ser_string(txn)
for key, value in unknowns:
    data += ser_string(key) + ser_string(value)
data += b'\x00\x00\x00'

original_settings = common.settings
try:
    common.settings = {}
    psbt = psbtObject.read_psbt(BytesIO(data))

    # MicroPython dictionaries may serialize the fields in a different order.
    serialized = BytesIO()
    psbt.serialize(serialized)
    serialized.seek(0)
    reparsed = psbtObject.read_psbt(serialized)
finally:
    common.settings = original_settings

for parsed in (psbt, reparsed):
    assert len(parsed.unknowns) == len(unknowns)
    for key, value in unknowns:
        assert parsed.get(parsed.unknowns[key]) == value
    assert parsed.get(parsed.txn) == txn
    assert parsed.num_inputs == 1
    assert parsed.num_outputs == 1

return_value.write(b'OK')
