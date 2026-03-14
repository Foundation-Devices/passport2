# SPDX-FileCopyrightText: © 2022 Seed Signer
# SPDX-License-Identifier: MIT
#
# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# compact_seedqr_decoder.py
#
# Compact SeedQR codec
#

from .data_encoder import DataEncoder
from .data_decoder import DataDecoder
from .data_sampler import DataSampler
from .qr_type import QRType


class CompactSeedQRDecoder(DataDecoder):
    def __init__(self):
        self.data = None

    def add_data(self, data):
        self.data = data

    def estimated_percent_complete(self):
        return 1 if self.data is not None else 0

    def is_complete(self):
        return self.data is not None

    def decode(self, **kwargs):
        from utils import get_words_from_seed

        (seed_phrase, error) = get_words_from_seed(self.data)

        if error is not None or seed_phrase is None:
            return None

        return seed_phrase

    def qr_type(self):
        return QRType.COMPACT_SEED_QR


class CompactSeedQREncoder(DataEncoder):
    def __init__(self):
        self.data = None

    def encode(self, data, is_binary=False, max_fragment_len=None):
        import trezorcrypto
        import math
        from utils import get_width_from_num_words
        import uio

        binary_str = uio.StringIO(11 * len(data))

        # Get indices in binary string of 11 bits per index
        for word in data:
            index = trezorcrypto.bip39.find_word(word)
            index_bin = '{:011b}'.format(index)
            binary_str.write(index_bin)

        binary_str = binary_str.getvalue()

        # Exclude checksum bits
        if len(data) == 24:
            binary_str = binary_str[:-8]

        if len(data) == 12:
            binary_str = binary_str[:-4]

        # Convert to binary
        width = get_width_from_num_words(len(data))
        as_bytes = bytearray(width)
        for i in range(0, width):
            as_bytes[i] = int('0b' + binary_str[i * 8:(i + 1) * 8], 2)

        self.data = as_bytes

    def next_part(self):
        return self.data


class CompactSeedQRSampler(DataSampler):
    # Any data can be accepted
    @classmethod
    def sample(cls, data):
        return True

    # Number of bytes required to successfully recognize this format
    @classmethod
    def min_sample_size(cls):
        return 16
