# SPDX-FileCopyrightText: 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# address_sampler.py - Indicate if the given data is a Bitcoin address
#

from .data_sampler import DataSampler


class AddressSampler(DataSampler):
    # Check if the given data looks like a Bitcoin address
    @classmethod
    def sample(cls, data):
        try:
            # TODO: Implement address sampler (not used yet though)
            return False
        except Exception as e:
            # Lots of files could contain non-UTF-8 data, so we just ignore these errors as expected
            return False

    # Number of bytes required to successfully recognize this format
    @classmethod
    def min_sample_size(cls):
        # https://blog.hubspot.com/marketing/bitcoin-address#:~:text=Bitcoin%20Address%20Example,%E2%80%9D%2C%20or%20%E2%80%9Cbc1%E2%80%9D.
        return 26
