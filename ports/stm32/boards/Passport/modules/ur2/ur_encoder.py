# SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: BSD-2-Clause-Patent
#
# ur_encoder.py
#

from .fountain_encoder import FountainEncoder
from .bytewords import *


class UREncoder:
    # Start encoding a (possibly) multi-part UR.
    def __init__(self, ur, max_fragment_len, first_seq_num=0, min_fragment_len=10):
        self.ur = ur
        self.fountain_encoder = FountainEncoder(
            ur.cbor, max_fragment_len, first_seq_num, min_fragment_len)

    # Encode a single-part UR.
    @staticmethod
    def encode(ur):
        body = Bytewords.encode(Bytewords_Style_minimal, ur.cbor)
        return UREncoder.encode_ur([ur.type, body])

    # `True` if the minimal number of parts to transmit the message have been
    # generated. Parts generated when this is `true` will be fountain codes
    # containing various mixes of the part data.
    def is_complete(self):
        return self.fountain_encoder.is_complete()

    # `True` if this UR can be contained in a single part. If `True`, repeated
    # calls to `next_part()` will all return the same single-part UR.
    def is_single_part(self):
        return self.fountain_encoder.is_single_part()

    def next_part(self):
        part = self.fountain_encoder.next_part()
        if self.is_single_part():
            return UREncoder.encode(self.ur)
        else:
            return UREncoder.encode_part(self.ur.type, part)

    @staticmethod
    def encode_part(type, part):
        seq = '{}-{}'.format(part.seq_num, part.seq_len)
        body = Bytewords.encode(Bytewords_Style_minimal, part.cbor())
        result = UREncoder.encode_ur([type, seq, body])
        return result

    @staticmethod
    def encode_uri(scheme, path_components):
        path = '/'.join(path_components)
        return ':'.join([scheme, path])

    @staticmethod
    def encode_ur(path_components):
        return UREncoder.encode_uri('ur', path_components)
