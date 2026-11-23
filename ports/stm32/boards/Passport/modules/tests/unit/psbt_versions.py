# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

from uio import BytesIO
from ustruct import pack

import common
from exceptions import FatalPSBTIssue
from psbt import psbtObject
from serializations import CTxOut, ser_string


txin = b'\x11' * 32 + pack('<I', 0) + b'\x00' + pack('<I', 0xffffffff)
txout = CTxOut(1000, b'\x00\x14' + b'\x22' * 20)
txn = pack('<i', 2) + b'\x01' + txin + b'\x01' + txout.serialize() + pack('<I', 0)


def read(fields):
    data = b'psbt\xff' + ser_string(b'\x00') + ser_string(txn)
    for key, value in fields:
        data += ser_string(key) + ser_string(value)
    return psbtObject.read_psbt(BytesIO(data + b'\x00\x00\x00'))


original_settings = common.settings
try:
    common.settings = {}
    for version in (1, 2, 0xffffffff):
        try:
            read(((b'\xfb', pack('<I', version)),))
        except FatalPSBTIssue:
            pass
        else:
            raise AssertionError('Unsupported PSBT version accepted')

    invalid_fields = [((b'\xfb', b'\x00' * length),) for length in (0, 1, 3, 5, 8)]
    invalid_fields += [((b'\xfbextra', pack('<I', 0)),),
                       ((b'\xfb', pack('<I', 0)), (b'\xfb', pack('<I', 0)))]
    for fields in invalid_fields:
        try:
            read(fields)
        except FatalPSBTIssue:
            pass
        else:
            raise AssertionError('Malformed PSBT version accepted')

    for fields, expected in (((), None), (((b'\xfb', pack('<I', 0)),), 0)):
        parsed = read(fields)
        assert parsed.psbt_version == expected
        serialized = BytesIO()
        parsed.serialize(serialized)
        serialized.seek(0)
        reparsed = psbtObject.read_psbt(serialized)
        assert reparsed.psbt_version == expected
        assert reparsed.get(reparsed.txn) == txn
finally:
    common.settings = original_settings

return_value.write(b'OK')
