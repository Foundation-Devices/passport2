# SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# ur2_codec.py
#
# UR 2.0 Codec
#
import math
import re

from .data_encoder import DataEncoder
from .data_decoder import DataDecoder, DecodeError
from .data_sampler import DataSampler
from .qr_type import QRType

from ur2.ur_decoder import URDecoder, URError
from ur2.ur_encoder import UREncoder

from ur2.cbor_lite import CBORDecoder, CBOREncoder, CBORError

from ur2.ur import UR


class UR2Decoder(DataDecoder):
    def __init__(self):
        self.decoder = URDecoder()

    # Decode the given data into the expected format
    def add_data(self, data):
        try:
            return self.decoder.receive_part(data)
        except URError as exc:
            raise DecodeError from exc

    def estimated_percent_complete(self):
        return self.decoder.estimated_percent_complete()

    def is_complete(self):
        return self.decoder.is_complete()

    def decode(self, decode_cbor_bytes=False):
        message = self.decoder.result
        if decode_cbor_bytes:
            try:
                cbor_decoder = CBORDecoder(message.cbor)
                (message, length) = cbor_decoder.decodeBytes()
            except CBORError as exc:
                raise DecodeError from exc

        return message

    def qr_type(self):
        return QRType.UR2


class UR2Encoder(DataEncoder):
    def __init__(self, args):
        self.ur_encoder = None
        self.type = None
        if isinstance(args, dict):
            self.prefix = args['prefix'] or 'bytes'
        else:
            self.prefix = 'bytes'

    # Encode the given data
    def encode(self, data, is_binary=False, max_fragment_len=200):
        # print('UR2Encoder: data="{}"'.format(data))
        if not hasattr(data, 'cbor'):
            encoder = CBOREncoder()
            # print('UR2: data={}'.format(to_str(data)))
            encoder.encodeBytes(data)
            data = encoder.get_bytes()
            ur_obj = UR(self.prefix, encoder.get_bytes())
        else:
            ur_obj = data

        # CBOR length of a UR2 part. Excluding the data itself on bytes which
        # must be of the resulting `max_fragment_len`.
        #
        # 85                                      # array(5)
        #    1A FFFFFFFF                          # unsigned(0xFFFFFFFF)
        #    1B FFFFFFFFFFFFFFFF                  # unsigned(0xFFFFFFFFFFFFFFFF)
        #    1B FFFFFFFFFFFFFFFF                  # unsigned(0xFFFFFFFFFFFFFFFF)
        #    1A FFFFFFFF                          # unsigned(0xFFFFFFFF)
        #    5B FFFFFFFFFFFFFFFF                  # bytes(0xFFFFFFFFFFFFFFFF)
        max_fragment_cbor = 1 + 5 + 9 + 9 + 5 + 2

        # "ur:" + prefix + "/99-999/" + max-fragment-cbor + CRC
        reserved_len = 3 + len(self.prefix) + len("/99-9999/") + max_fragment_cbor + (4 * 2)

        # Divide in half the maximum fragment length as each byteword encoded byte takes two characters.
        max_fragment_len = (max_fragment_len - reserved_len) // 2
        self.ur_encoder = UREncoder(ur_obj, max_fragment_len)

    # UR2.0's next_part() returns the initial pieces split into max_fragment_len bytes, but then switches over to
    # an infinite series of encodings that combine various pieces of the data in an attempt to fill in any holes missed.
    def next_part(self):
        return self.ur_encoder.next_part()


class UR2Sampler(DataSampler):
    # Check if the given bytes look like UR2 data
    # Return True if it matches or False if not
    @classmethod
    def sample(cls, data):
        try:
            # Rather than try a complex regex here, we just let the decoder try to decode and if it fails.
            # it must not be UR2.
            decoder = URDecoder()
            result = decoder.receive_part(data)
            return result
        except Exception as e:
            return False

    # Number of bytes required to successfully recognize this format
    @classmethod
    def min_sample_size(cls):
        return 20
