# SPDX-FileCopyrightText: 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
from .bech32_version import Bech32_Version_Origin, Bech32_Version_Bis

CHARSET = 'qpzry9x8gf2tvdw0s3jn54khce6mua7l'
GENERATOR = [0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3]


def polymod(values):
    chk = 1
    for p in range(len(values)):
        top = chk >> 25
        chk = ((chk & 0x1FFFFFF) << 5) ^ values[p]
        for i in range(6):
            if (top >> i) & 1:
                chk ^= GENERATOR[i]

    return chk


def hrp_expand(hrp):
    ret = []
    for p in range(len(hrp)):
        ret.append(ord(hrp[p]) >> 5)

    ret.append(0)
    for p in range(len(hrp)):
        ret.append(ord(hrp[p]) & 31)

    return ret


def verify_checksum(hrp, data, version):
    header = []
    if hrp:
        header = hrp_expand(hrp)
    else:
        header = [0]
    check = 1 if version == Bech32_Version_Origin else 0x3fffffff
    header.extend(data)
    return polymod(header) == check


def create_checksum(hrp, data, bech32_version):
    if hrp is not None:
        values = hrp_expand(hrp)
        values.extend(data)
        values.extend([0, 0, 0, 0, 0, 0])
    else:
        values = [0]
        values.extend(data)
        values.extend([0, 0, 0, 0, 0, 0])

    check = 1 if bech32_version == Bech32_Version_Origin else 0x3fffffff

    mod = polymod(values) ^ check
    ret = []
    for p in range(6):
        ret.append((mod >> (5 * (5 - p))) & 31)

    return bytearray(ret)


def encode(hrp, data, version):
    checksum = create_checksum(hrp, data, version)
    combined = data + checksum
    if hrp is not None:
        ret = hrp + '1'
    else:
        ret = ''

    for p in range(len(combined)):
        ret += CHARSET[combined[p]]

    return ret


def decode_bc32(bech_string):
    data = []
    for p in range(len(bech_string)):
        d = CHARSET.find(bech_string[p])
        if d == -1:
            return None
        data.append(d)

    if not verify_checksum(None, data, Bech32_Version_Bis):
        return None

    # We return a tuple here instead of a JS object
    return (None, data[0:len(data) - 6])


def decode(bech_string):
    has_lower = False
    has_upper = False
    bech_len = len(bech_string)
    for p in range(bech_len):
        if ord(bech_string[p]) < 33 or ord(bech_string[p]) > 126:
            return None
        if ord(bech_string[p]) >= 97 and ord(bech_string[p]) <= 122:
            has_lower = True
        if ord(bech_string[p]) >= 65 and ord(bech_string[p]) <= 90:
            has_upper = True

    if has_lower and has_upper:
        return None

    bech_string = bech_string.lower()
    pos = bech_string.rfind('1')
    if pos == -1:
        return decode_bc32(bech_string)

    if pos < 1 or pos + 7 > bech_len or bech_len > 90:
        return None

    hrp = bech_string[0:pos]
    data = []
    for p in range(pos + 1, bech_len):
        d = CHARSET.find(bech_string[p])
        if d == -1:
            return None
        data.append(d)

    if not verify_checksum(hrp, data, Bech32_Version_Origin):
        return None

    return (hrp, data[0: len(data) - 6])
