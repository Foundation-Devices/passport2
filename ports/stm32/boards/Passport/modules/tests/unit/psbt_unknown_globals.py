# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Unknown and proprietary fields must survive all PSBT maps without interpretation.

from uio import BytesIO
from ustruct import pack

import common
from psbt import psbtObject
from serializations import CTxOut, ser_string


# Unsigned transaction with one input and one output.
txin = (b'\x11' * 32) + pack('<I', 0) + b'\x00' + pack('<I', 0xffffffff)
txout = CTxOut(1000, b'\x00\x14' + b'\x22' * 20)
txn = pack('<i', 2) + b'\x01' + txin + b'\x01' + txout.serialize() + pack('<I', 0)
unknowns = (
    (b'\x50extra', b'unknown value'),
    (b'\xfc\x04test\x00extra', b'proprietary value'),
)
# Type 0x16 is a Taproot derivation only in the input map, and 0x07 only
# in the output map. Elsewhere these opaque values must not be decoded.
global_fields = unknowns + ((b'\x16collision', b'raw global'), (b'\x07collision', b''))
input_fields = unknowns + ((b'\x50second', b'\x00\xff' * 100),)
output_fields = unknowns + ((b'\x16collision', b'raw output'),)
tap_key = b'\x33' * 32
tap_path = b'\x00' + pack('<II', 0x12345678, 0)


def encode_map(fields):
    return b''.join(ser_string(key) + ser_string(value) for key, value in fields) + b'\x00'


data = b'psbt\xff' + encode_map(((b'\x00', txn),) + global_fields)
data += encode_map(input_fields + ((b'\x16' + tap_key, tap_path),))
data += encode_map(output_fields + ((b'\x07' + tap_key, tap_path),))

original_settings = common.settings
try:
    common.settings = {}
    psbt = psbtObject.read_psbt(BytesIO(data))
    # Known Taproot derivations still use structured serialization.
    for scope in (psbt.inputs[0], psbt.outputs[0]):
        assert scope.parse_subpaths(0x12345678) == 1

    # MicroPython dictionaries may serialize the fields in a different order.
    serialized = BytesIO()
    psbt.serialize(serialized)
    serialized.seek(0)
    reparsed = psbtObject.read_psbt(serialized)
    for scope in (reparsed.inputs[0], reparsed.outputs[0]):
        assert scope.parse_subpaths(0x12345678) == 1
        assert scope.tap_subpaths[tap_key] == ([0x12345678, 0], [])
finally:
    common.settings = original_settings

for parsed in (psbt, reparsed):
    for scope, fields in ((parsed, global_fields), (parsed.inputs[0], input_fields),
                          (parsed.outputs[0], output_fields)):
        assert len(scope.unknowns) == len(fields)
        for key, value in fields:
            assert scope.get(scope.unknowns[key]) == value
    assert parsed.get(parsed.txn) == txn
    assert parsed.num_inputs == 1
    assert parsed.num_outputs == 1

return_value.write(b'OK')
