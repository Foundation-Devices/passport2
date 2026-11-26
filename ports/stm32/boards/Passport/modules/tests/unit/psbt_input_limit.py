# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# A PSBT with more inputs than Passport can sign is refused as soon as the input
# count is read, before any input is parsed.

from uio import BytesIO
from ustruct import pack

import common
import constants
from exceptions import FatalPSBTIssue
from psbt import psbtObject
from serializations import CTxOut, ser_compact_size, ser_string


def read(count):
    txins = b''.join(pack('<I', idx) + b'\x11' * 28 + pack('<I', 0) + b'\x00' + pack('<I', 0xffffffff)
                     for idx in range(count))
    txout = CTxOut(1000, b'\x00\x14' + b'\x22' * 20)
    txn = (pack('<i', 2) + ser_compact_size(count) + txins + b'\x01' + txout.serialize() +
           pack('<I', 0))
    data = b'psbt\xff' + ser_string(b'\x00') + ser_string(txn) + b'\x00'
    # An empty map for each input, then the output.
    data += b'\x00' * count + b'\x00'
    return psbtObject.read_psbt(BytesIO(data))


original_settings = common.settings
original_limit = constants.PSBT_MAX_INPUTS
try:
    common.settings = {}
    constants.PSBT_MAX_INPUTS = 3

    assert read(3).num_inputs == 3

    try:
        read(4)
    except FatalPSBTIssue as e:
        assert str(e) == ('This transaction has too many inputs for Passport to sign.\n\n'
                          'Split it into smaller transactions in your wallet coordinator '
                          'and try again.'), str(e)
    else:
        raise AssertionError('PSBT over the input limit accepted')
finally:
    common.settings = original_settings
    constants.PSBT_MAX_INPUTS = original_limit

return_value.write(b'OK')
