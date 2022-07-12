# SPDX-FileCopyrightText: 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# multisig_config_sampler.py
#
# Sampler for Multisig configuration files
#

import ure
from .data_sampler import DataSampler


class MultisigConfigSampler(DataSampler):
    # Check if the given bytes look like a multisig configuration file.
    # Return True if it matches or False if not.
    @classmethod
    def sample(cls, data):
        try:
            return data.find(b'Name:') >= 0 and data.find(b'Policy:') >= 0
        except Exception as e:
            # Lots of files could contain non-UTF-8 data, so we just ignore these errors as expected
            return False

    # Number of bytes required to successfully recognize this format
    # Zero means it potentially needs the entire file, but you can call
    # sample() at any time to test the data.
    @classmethod
    def min_sample_size(cls):
        return 0
