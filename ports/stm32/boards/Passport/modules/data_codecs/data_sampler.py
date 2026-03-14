# SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# data_sampler.py
#
# Base class for all data samplers
#


# Determine if the provided data matches the format of the sampler.
class DataSampler:
    # Return True if data matches or False if not
    @classmethod
    def sample(cls, data):
        pass

    # Number of bytes required to successfully recognize this format
    @classmethod
    def min_sample_size(cls):
        return 1
