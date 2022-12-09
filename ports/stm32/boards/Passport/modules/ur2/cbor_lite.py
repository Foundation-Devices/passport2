# SPDX-FileCopyrightText: 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: BSD-2-Clause-Patent
#
# cbor_lite.py
#

# From: https://bitbucket.org/isode/cbor-lite/raw/6c770624a97e3229e3f200be092c1b9c70a60ef1/include/cbor-lite/codec.h

# This file is part of CBOR-lite which is copyright Isode Limited
# and others and released under a MIT license. For details, see the
# COPYRIGHT.md file in the top-level folder of the CBOR-lite software
# distribution.

from micropython import const


def bit_length(n):
    return len(bin(abs(n))) - 2


Flag_None = const(0)
Flag_Require_Minimal_Encoding = const(1)

Tag_Major_unsignedInteger = const(0)
Tag_Major_negativeInteger = const(1 << 5)
Tag_Major_byteString = const(2 << 5)
Tag_Major_textString = const(3 << 5)
Tag_Major_array = const(4 << 5)
Tag_Major_map = const(5 << 5)
Tag_Major_semantic = const(6 << 5)
Tag_Major_floatingPoint = const(7 << 5)
Tag_Major_simple = const(7 << 5)
Tag_Major_mask = const(0xe0)

Tag_Minor_length1 = const(24)
Tag_Minor_length2 = const(25)
Tag_Minor_length4 = const(26)
Tag_Minor_length8 = const(27)

Tag_Minor_false = const(20)
Tag_Minor_true = const(21)
Tag_Minor_null = const(22)
Tag_Minor_undefined = const(23)
Tag_Minor_half_float = const(25)
Tag_Minor_singleFloat = const(26)
Tag_Minor_doubleFloat = const(27)

Tag_Minor_dateTime = const(0)
Tag_Minor_epochDateTime = const(1)
Tag_Minor_positiveBignum = const(2)
Tag_Minor_negativeBignum = const(3)
Tag_Minor_decimalFraction = const(4)
Tag_Minor_bigFloat = const(5)
Tag_Minor_convertBase64Url = const(21)
Tag_Minor_convertBase64 = const(22)
Tag_Minor_convertBase16 = const(23)
Tag_Minor_cborEncodedData = const(24)
Tag_Minor_uri = const(32)
Tag_Minor_base64Url = const(33)
Tag_Minor_base64 = const(34)
Tag_Minor_regex = const(35)
Tag_Minor_mimeMessage = const(36)
Tag_Minor_embeddedJSON = const(262)
Tag_Minor_selfDescribeCbor = const(55799)
Tag_Minor_mask = 0x1f
Tag_Undefined = Tag_Major_semantic + Tag_Minor_undefined


def get_byte_length(value):
    if value < 24:
        return 0

    return (bit_length(value) + 7) // 8


class CBOREncoder:
    def __init__(self):
        self.buf = bytearray()

    def get_bytes(self):
        return self.buf

    def encodeTagAndAdditional(self, tag, additional):
        self.buf.append(tag + additional)
        return 1

    def encodeTagAndValue(self, tag, value):
        length = get_byte_length(value)

        # 5-8 bytes required, use 8 bytes
        if length >= 5 and length <= 8:
            self.encodeTagAndAdditional(tag, Tag_Minor_length8)
            self.buf.append((value >> 56) & 0xff)
            self.buf.append((value >> 48) & 0xff)
            self.buf.append((value >> 40) & 0xff)
            self.buf.append((value >> 32) & 0xff)
            self.buf.append((value >> 24) & 0xff)
            self.buf.append((value >> 16) & 0xff)
            self.buf.append((value >> 8) & 0xff)
            self.buf.append(value & 0xff)

        # 3-4 bytes required, use 4 bytes
        elif length == 3 or length == 4:
            self.encodeTagAndAdditional(tag, Tag_Minor_length4)
            self.buf.append((value >> 24) & 0xff)
            self.buf.append((value >> 16) & 0xff)
            self.buf.append((value >> 8) & 0xff)
            self.buf.append(value & 0xff)

        elif length == 2:
            self.encodeTagAndAdditional(tag, Tag_Minor_length2)
            self.buf.append((value >> 8) & 0xff)
            self.buf.append(value & 0xff)

        elif length == 1:
            self.encodeTagAndAdditional(tag, Tag_Minor_length1)
            self.buf.append(value & 0xff)

        elif length == 0:
            self.encodeTagAndAdditional(tag, value)

        else:
            raise Exception(
                "Unsupported byte length of {} for value in encodeTagAndValue()".format(length))

        encoded_size = 1 + length
        return encoded_size

    def encodeTagSemantic(self, value):
        return self.encodeTagAndValue(Tag_Major_semantic, value)

    def encodeUndefined(self, value):
        return self.encodeTagAndValue(Tag_Major_semantic, value)

    def encodeUnsigned(self, value):
        return self.encodeTagAndValue(Tag_Major_unsignedInteger, value)

    def encodeNegative(self, value):
        return self.encodeTagAndValue(Tag_Major_negativeInteger, value)

    def encodeInteger(self, value):
        if value >= 0:
            return self.encodeUnsigned(value)
        else:
            return self.encodeNegative(value)

    def encodeBool(self, value):
        return self.encodeTagAndValue(Tag_Major_simple, Tag_Minor_true if value else Tag_Minor_false)

    def encodeBytes(self, value):
        length = self.encodeTagAndValue(Tag_Major_byteString, len(value))
        self.buf += value
        return length + len(value)

    def encodeEncodedBytesPrefix(self, value):
        length = self.encodeTagAndValue(
            Tag_Major_semantic, Tag_Minor_cborEncodedData)
        return length + self.encodeTagAndAdditional(Tag_Major_bytestring, value)

    def encodeEncodedBytes(self, value):
        length = self.encodeTagAndValue(
            Tag_Major_semantic, Tag_Minor_cborEncodedData)
        return length + self.encodeBytes(value)

    def encodeText(self, value):
        str_len = len(value)
        length = self.encodeTagAndValue(Tag_Major_textString, str_len)
        # print(bytes(value, 'utf8'))
        self.buf.extend(bytes(value, 'utf8'))
        return length + str_len

    def encodeArraySize(self, value):
        return self.encodeTagAndValue(Tag_Major_array, value)

    def encodeMapSize(self, value):
        return self.encodeTagAndValue(Tag_Major_map, value)

    def encodeJSON(self, value):
        length = self.encodeTagAndValue(
            Tag_Major_semantic, Tag_Minor_embeddedJSON)
        return length + self.encodeBytes(value)


class CBORDecoder:
    def __init__(self, buf):
        self.buf = buf
        self.pos = 0

    def decodeTagAndAdditional(self, flags=Flag_None):
        if self.pos == len(self.buf):
            raise Exception("Not enough input")
        octet = self.buf[self.pos]
        self.pos += 1
        tag = octet & Tag_Major_mask
        additional = octet & Tag_Minor_mask
        return (tag, additional, 1)

    def decodeTagAndValue(self, flags):
        end = len(self.buf)

        if self.pos == end:
            raise Exception("Not enough input")

        (tag, additional, length) = self.decodeTagAndAdditional(flags)
        if additional < Tag_Minor_length1:
            value = additional
            return (tag, value, length)

        value = 0
        if additional == Tag_Minor_length8:
            if end - self.pos < 8:
                raise Exception("Not enough input")
            for shift in [56, 48, 40, 32, 24, 16, 8, 0]:
                value |= self.buf[self.pos] << shift
                self.pos += 1
            if ((flags & Flag_Require_Minimal_Encoding) and value == 0):
                raise Exception("Encoding not minimal")
            return (tag, value, self.pos)
        elif additional == Tag_Minor_length4:
            if end - self.pos < 4:
                raise Exception("Not enough input")
            for shift in [24, 16, 8, 0]:
                value |= self.buf[self.pos] << shift
                self.pos += 1
            if ((flags & Flag_Require_Minimal_Encoding) and value == 0):
                raise Exception("Encoding not minimal")
            return (tag, value, self.pos)
        elif additional == Tag_Minor_length2:
            if end - self.pos < 2:
                raise Exception("Not enough input")
            for shift in [8, 0]:
                value |= self.buf[self.pos] << shift
                self.pos += 1
            if ((flags & Flag_Require_Minimal_Encoding) and value == 0):
                raise Exception("Encoding not minimal")
            return (tag, value, self.pos)
        elif additional == Tag_Minor_length1:
            if end - self.pos < 1:
                raise Exception("Not enough input")
            value |= self.buf[self.pos]
            self.pos += 1
            if ((flags & Flag_Require_Minimal_Encoding) and value == 0):
                raise Exception("Encoding not minimal")
            return (tag, value, self.pos)

        raise Exception("Bad additional value")

    def decodeTagSemantic(self, flags=Flag_None):
        (tag, value, length) = self.decodeTagAndValue(flags)
        if tag != Tag_Major_semantic:
            raise Exception("Expected Tag_Major_semantic, but found {}".format(tag))
        return (value, length)

    def decodeUndefined(self, flags=Flag_None):
        (tag, value, length) = self.decodeTagAndValue(flags)
        if tag != Tag_Major_semantic:
            raise Exception("Expected Tag_Major_semantic ({}), but found {}".format(
                Tag_Major_semantic, tag))
        return (value, length)

    def decodeUnsigned(self, flags=Flag_None):
        (tag, value, length) = self.decodeTagAndValue(flags)
        if tag != Tag_Major_unsignedInteger:
            raise Exception("Expected Tag_Major_unsignedInteger ({}), but found {}".format(
                Tag_Major_unsignedInteger, tag))
        return (value, length)

    def decodeNegative(self, flags=Flag_None):
        (tag, value, length) = self.decodeTagAndValue(flags)
        if tag != Tag_Major_negativeInteger:
            raise Exception(
                "Expected Tag_Major_negativeInteger, but found {}".format(tag))
        return (value, length)

    def decodeInteger(self, flags=Flag_None):
        (tag, value, length) = self.decodeTagAndValue(flags)
        if tag == Tag_Major_unsignedInteger:
            return (value, length)
        elif tag == Tag_Major_negativeInteger:
            # TODO: Need to properly test negative integers (although we don't use them).  Need to use struct.unpack()?
            return (-1 - value, length)

    def decodeBool(self, flags=Flag_None):
        (tag, value, length) = self.decodeTagAndValue(flags)
        if tag == Tag_Major_simple:
            if value == Tag_Minor_true:
                return (True, length)
            elif value == Tag_Minor_false:
                return (False, length)
            raise Exception("Not a Boolean")
        raise Exception("Not Simple/Boolean")

    def decodeBytes(self, flags=Flag_None):
        # First value is the length of the bytes that follow
        (tag, byte_length, size_length) = self.decodeTagAndValue(flags)
        if tag != Tag_Major_byteString:
            raise Exception("Not a byteString")

        end = len(self.buf)
        if end - self.pos < byte_length:
            raise Exception("Not enough input")

        value = bytes(self.buf[self.pos: self.pos + byte_length])
        self.pos += byte_length
        return (value, size_length + byte_length)

    def decodeEncodedBytesPrefix(self, flags=Flag_None):
        (tag, value, length1) = self.decodeTagAndValue(flags)
        if tag != Tag_Major_semantic or value != Tag_Minor_cborEncodedData:
            raise Exception("Not CBOR Encoded Data")

        (tag, value, length2) = self.decodeTagAndValue(flags)
        if tag != Tag_Major_byteString:
            raise Exception("Not byteString")

        return (tag, value, length1 + length2)

    def decodeEncodedBytes(self, flags=Flag_None):
        (tag, minor_tag, tag_length) = self.decodeTagAndValue(flags)
        if tag != Tag_Major_semantic or minor_tag != Tag_Minor_cborEncodedData:
            raise Exception("Not CBOR Encoded Data")

        (value, length) = self.decodeBytes(flags)
        return (value, tag_length + length)

    def decodeText(self, flags=Flag_None):
        # First value is the length of the bytes that follow
        (tag, byte_length, size_length) = self.decodeTagAndValue(flags)
        if tag != Tag_Major_textString:
            raise Exception("Not a textString")

        end = len(self.buf)
        if end - self.pos < byte_length:
            raise Exception("Not enough input")

        value = bytes(self.buf[self.pos: self.pos + byte_length])
        self.pos += byte_length
        return (value, size_length + byte_length)

    def decodeArraySize(self, flags=Flag_None):
        (tag, value, length) = self.decodeTagAndValue(flags)

        if tag != Tag_Major_array:
            raise Exception(
                "Expected Tag_Major_array, but found {}".format(tag))
        return (value, length)

    def decodeMapSize(self, flags=Flag_None):
        (tag, value, length) = self.decodeTagAndValue(flags)
        if tag != Tag_Major_map:
            raise Exception("Expected Tag_Major_map, but found {}".format(tag))
        return (value, length)
