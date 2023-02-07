# SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# seed_sampler.py
#
# Sampler for PSBT formats
#

from .data_sampler import DataSampler


class SeedSampler(DataSampler):
    # Check if the given bytes look like a seed.
    # Return True if it matches or False if not.
    @classmethod
    def sample(cls, data):
        try:
            s = data.decode('utf-8')
            words = s.split(' ')
            num_words = len(words)
            return num_words == 12 or num_words == 24
        except Exception as e:
            # Lots of files could contain non-UTF-8 data, so we just ignore these errors as expected
            return False

    # Number of bytes required to successfully recognize this format
    @classmethod
    def min_sample_size(cls):
        return 0
