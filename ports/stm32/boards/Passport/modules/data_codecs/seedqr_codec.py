# SPDX-FileCopyrightText: © 2022 Seed Signer
# SPDX-License-Identifier: MIT
#
# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# seedqr_decoder.py
#
# SeedQR codec
#

from .data_encoder import DataEncoder
from .data_decoder import DataDecoder
from .data_sampler import DataSampler
from .qr_type import QRType


class SeedQRDecoder(DataDecoder):
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


class SeedQREncoder(DataEncoder):
    def __init__(self, _args):
        self.data = None

    def encode(self, data, is_binary=False, max_fragment_len=None):
        import trezorcrypto
        import uio

        data_str = uio.StringIO(4 * len(data))

        # Get indices in binary string of 11 bits per index
        for word in data:
            index = trezorcrypto.bip39.find_word(word)
            data_str.write('{:04d}'.format(index))

        self.data = data_str.getvalue()

    def next_part(self):
        return self.data


class SeedQRSampler(DataSampler):
    # Any data can be accepted
    @classmethod
    def sample(cls, data):
        return True

    # Number of bytes required to successfully recognize this format
    @classmethod
    def min_sample_size(cls):
        return 1
