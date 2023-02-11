# SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# qr_decoder.py
#
# Basic QR codec
#

from .data_encoder import DataEncoder
from .data_decoder import DataDecoder
from .data_sampler import DataSampler
from .qr_type import QRType


class QRDecoder(DataDecoder):
    def __init__(self):
        self.data = None

    def add_data(self, data):
        self.data = data

    def estimated_percent_complete(self):
        return 1 if self.data is not None else 0

    def is_complete(self):
        return self.data is not None

    def decode(self, **kwargs):
        return self.data

    def qr_type(self):
        return QRType.QR


class QREncoder(DataEncoder):
    def __init__(self, _args):
        self.data = None

    def encode(self, data, max_fragment_len=None):
        self.data = data

    def next_part(self):
        return self.data


class QRSampler(DataSampler):
    # Any data can be accepted
    @classmethod
    def sample(cls, data):
        return True

    # Number of bytes required to successfully recognize this format
    @classmethod
    def min_sample_size(cls):
        return 1
