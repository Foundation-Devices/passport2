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
from .data_decoder import DataDecoder
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

    # Decode the given data into the expected format
    def add_data(self, data):
        try:
            self.workloads.add(data)
            self._received_parts, self._total_parts = self.workloads.get_progress()
            return True
        except Exception as e:
            self.error = '{}'.format(e)
            return False

    def received_parts(self):
        return self._received_parts

    def total_parts(self):
        return self._total_parts

    def is_complete(self):
        return self.workloads.is_complete()

    def get_error(self):
        return self.error

    def get_ur_prefix(self):
        return 'bytes'  # TODO: Get the type from the UR1 decoder

    def decode(self, **kwargs):
        from common import system
        try:
            # system.show_busy_bar()
            encoded_data = decode_ur(self.workloads.workloads)
            # system.hide_busy_bar()
            # print('UR1: encoded_data={}'.format(encoded_data))
            data = unhexlify(encoded_data)  # TODO: Should this be optional (e.g., PSBT in binary)?
            # print('UR1: data={}'.format(data))
            return data
        except Exception as e:
            self.error = '{}'.format(e)
            # print('UR1Decoder.decode() ERROR: {}'.format(e))
            return None

    def get_data_format(self):
        return QRType.UR1


class UR1Encoder(DataEncoder):
    def __init__(self, _args):
        self.parts = []
        self.next_index = 0
        self.qr_sizes = [60, 200, 500]

    # def get_num_supported_sizes(self):
    #     return len(self.qr_sizes)

    def get_max_len(self, index):
        if index < 0 or index >= len(self.qr_sizes):
            return 0
        return self.qr_sizes[index]

    # Encode the given data
    def encode(self, data, is_binary=False, max_fragment_len=500):
        from ubinascii import hexlify

        # Convert from
        if isinstance(data, str):
            data = data.encode('utf8')

        if not is_binary:
            data = hexlify(data)
            # print('UR1: hex data={}'.format(data))
            data = data.decode('utf8')

        # print('UR1: data={}'.format(data))

        self.parts = encode_ur(data, fragment_capacity=max_fragment_len)

    def next_part(self):
        from utils import to_str
        part = self.parts[self.next_index]
        self.next_index = (self.next_index + 1) % len(self.parts)
        # print('UR1: part={}'.format(to_str(part)))
        return part.upper()

    # Return any error info
    def get_error(self):
        return None


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
