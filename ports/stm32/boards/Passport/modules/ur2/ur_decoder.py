# SPDX-FileCopyrightText: 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: BSD-2-Clause-Patent
#
# ur_decoder.py
#

from .ur import UR
from .fountain_encoder import FountainEncoder, Part as FountainEncoderPart
from .fountain_decoder import FountainDecoder, FountainError
from .bytewords import *
from .utils import drop_first, is_ur_type


class URError(Exception):
    pass


class URDecoder:
    def __init__(self):
        self.fountain_decoder = FountainDecoder()
        self._expected_type = None
        self.result = None

    @staticmethod
    def decode(str):
        (type, components) = URDecoder.parse(str)
        if len(components) == 0:
            raise URError('invalid path length')

        body = components[0]
        return URDecoder.decode_by_type(type, body)

    @staticmethod
    def decode_by_type(type, body):
        cbor = Bytewords.decode(Bytewords_Style_minimal, body)
        return UR(type, cbor)

    @staticmethod
    def parse(str):
        # Don't consider case
        lowered = str.lower()

        # Validate URI scheme
        if not lowered.startswith('ur:'):
            raise URError('Invalid scheme')

        path = drop_first(lowered, 3)

        # Split the remainder into path components
        components = path.split('/')

        # Make sure there are at least two path components
        if len(components) < 2:
            raise URError('malformed UR path components')

        # Validate the type
        type = components[0]
        if not is_ur_type(type):
            raise URError('invalid UR type')

        comps = components[1:]  # Don't include the ur type
        return (type, comps)

    @staticmethod
    def parse_sequence_component(str):
        comps = str.split('-')
        if len(comps) != 2:
            raise URError('invalid sequence component')
        seq_num = int(comps[0])
        seq_len = int(comps[1])
        # print('seq_num={} seq_len={}'.format(seq_num, seq_len))
        if seq_num < 1 or seq_len < 1:
            raise URError('invalid sequence numbers')
        return (seq_num, seq_len)

    def validate_part(self, type):
        if self._expected_type is None:
            if not is_ur_type(type):
                return False
            self._expected_type = type
            return True
        else:
            return type == self._expected_type

    def receive_part(self, str):
        # Don't process the part if we're already done
        if self.result is not None:
            return False

        # Don't continue if this part doesn't validate
        (type, components) = URDecoder.parse(str)
        if not self.validate_part(type):
            return False

        # If this is a single-part UR then we're done
        if len(components) == 1:
            body = components[0]
            self.result = self.decode_by_type(type, body)
            return True

        # Multi-part URs must have two path components: seq/fragment
        if len(components) != 2:
            raise InvalidPathLength()
        seq = components[0]
        fragment = components[1]

        # Parse the sequence component and the fragment, and make sure they agree.
        (seq_num, seq_len) = URDecoder.parse_sequence_component(seq)
        cbor = Bytewords.decode(Bytewords_Style_minimal, fragment)
        part = FountainEncoderPart.from_cbor(cbor)
        if seq_num != part.seq_num or seq_len != part.seq_len:
            raise URError('sequence numbers mismatch')

        # Process the part
        try:
            self.fountain_decoder.receive_part(part)
            if self.fountain_decoder.is_complete():
                self.result = UR(type, self.fountain_decoder.result_message())
        except FountainError as exc:
            raise URError('failed to receive part') from exc

        return True

    def estimated_percent_complete(self):
        return self.fountain_decoder.estimated_percent_complete()

    def is_complete(self):
        return self.result is not None

    def result(self):
        return self.result
