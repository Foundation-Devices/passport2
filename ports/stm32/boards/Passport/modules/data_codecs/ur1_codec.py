# SPDX-FileCopyrightText: 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# ur1_codec.py
#
# UR 1.0 codec
#
import re
from ubinascii import unhexlify

from .data_encoder import DataEncoder
from .data_decoder import DataDecoder, DecodeError
from .data_sampler import DataSampler
from .qr_type import QRType
from ur1.decode_ur import decode_ur, extract_single_workload, Workloads
from ur1.encode_ur import encode_ur


class UR1Decoder(DataDecoder):
    def __init__(self):
        self.workloads = Workloads()
        self._received_parts = 0
        self._total_parts = 0
        self.error = None

    def add_data(self, data):
        try:
            self.workloads.add(data)
        except ValueError as exc:
            raise DecodeError from exc

        self._received_parts, self._total_parts = self.workloads.get_progress()

    def estimated_percent_complete(self):
        return int((self._received_parts * 100) / self._total_parts)

    def is_complete(self):
        return self.workloads.is_complete()

    def decode(self, **kwargs):
        # XXX: This should be optional (e.g., PSBT in binary).
        #
        # But the UR1 standard is deprecated.
        return unhexlify(decode_ur(self.workloads.workloads))

    def qr_type(self):
        return QRType.UR1


class UR1Encoder(DataEncoder):
    def __init__(self, _args):
        self.parts = []
        self.next_index = 0

    # Encode the given data
    def encode(self, data, is_binary=False, max_fragment_len=500):
        from ubinascii import hexlify

        # Convert from
        if isinstance(data, str):
            data = data.encode('utf8')

        if not is_binary:
            data = hexlify(data)
            data = data.decode('utf8')

        self.parts = encode_ur(data, fragment_capacity=max_fragment_len)

    def next_part(self):
        from utils import to_str
        part = self.parts[self.next_index]
        self.next_index = (self.next_index + 1) % len(self.parts)
        return part.upper()


class UR1Sampler(DataSampler):
    # Check if the given bytes look like UR1 data
    # Return True if it matches or False if not
    @classmethod
    def sample(cls, data):
        r = re.compile('^ur:bytes/')  # Don't look for the n of m count anymore
        m = r.match(data.lower())
        return m is not None

    # Number of bytes required to successfully recognize this format
    @classmethod
    def min_sample_size(cls):
        return 20
