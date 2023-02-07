# SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
from .bech32 import encode, decode
from .bech32_version import Bech32_Version_Origin, Bech32_Version_Bis
from ubinascii import hexlify
import gc


def convert_bits(data, from_bits, to_bits, pad):
    acc = 0
    bits = 0
    new_size = int(len(data) * from_bits / to_bits)
    if pad:
        new_size += 1

    ret = bytearray(new_size)
    maxv = (1 << to_bits) - 1
    i = 0

    for p in range(len(data)):
        value = data[p]
        if value < 0 or value >> from_bits != 0:
            return None

        acc = (acc << from_bits) | value
        bits += from_bits
        while bits >= to_bits:
            bits -= to_bits
            ret[i] = (acc >> bits) & maxv
            i += 1

    if pad:
        if bits > 0:
            ret[i] = (acc << (to_bits - bits)) & maxv
        else:
            ret = ret[:-1]
    elif bits >= from_bits or (acc << (to_bits - bits)) & maxv:
        return None

    return ret

# NOTE: Segwit functions not needed, so not ported


def encode_bc32_data(data):
    u82u5 = convert_bits(data, 8, 5, True)
    # print('u82u5={}'.format(u82u5))
    res = u82u5
    if u82u5 is None:
        raise ValueError('Invalid bc32 data')
    else:
        return encode(None, res, Bech32_Version_Bis)


def decode_bc32_data(data):
    result = decode(data)
    if result is not None:
        b = bytearray(result[1])
        res = convert_bits(b, 5, 8, False)
        if res is not None:
            return hexlify(res).decode()
        return None
    else:
        return None
