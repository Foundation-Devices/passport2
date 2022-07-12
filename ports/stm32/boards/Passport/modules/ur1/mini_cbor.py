# SPDX-FileCopyrightText: 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
from ubinascii import hexlify
from ubinascii import unhexlify as a2b_hex

# This an simple cbor implementation which is just using on BCR-05


def compose_header(length):
    if length > 0 and length <= 23:
        header = bytearray(1)
        header[0] = 0x40 + length
    elif length >= 24 and length <= 255:
        tag = bytearray(1)
        tag[0] = 0x58
        header = tag + length.to_bytes(1, 'big')
    elif length >= 256 and length <= 65535:
        tag = bytearray(1)
        tag[0] = 0x59
        header = tag + length.to_bytes(2, 'big')
    elif length >= 65536 and length <= 2 ** 32 - 1:
        tag = bytearray(1)
        tag[0] = 0x60
        header = tag + length.to_bytes(4, 'big')
    else:
        raise ValueError('length is too big')

    return header


def encode_simple_cbor(data):
    buffer_data = a2b_hex(data)
    buffer_len = len(buffer_data)
    if buffer_len <= 0 or buffer_len >= 2 ** 32:
        raise ValueError('length is too big')

    header = compose_header(buffer_len)

    encoded = header + buffer_data
    return encoded


def decode_simple_cbor(data):
    data_buffer = a2b_hex(data)

    data_len = len(data_buffer)
    if data_len <= 0:
        raise ValueError('invalid length (<=0)')

    header = data_buffer[0]
    if header < 0x58:
        data_length = header - 0x40
        return hexlify(data_buffer[1:1 + data_length]).decode()
    elif header == 0x58:
        data_length = int.from_bytes(data_buffer[1:2], 'big')
        return hexlify(data_buffer[2:2 + data_length]).decode()
    elif header == 0x59:
        data_length = int.from_bytes(data_buffer[1:3], 'big')
        return hexlify(data_buffer[3:3 + data_length]).decode()
    elif header == 0x60:
        data_length = int.from_bytes(data_buffer[1:5], 'big')
        return hexlify(data_buffer[5:5 + data_length]).decode()
