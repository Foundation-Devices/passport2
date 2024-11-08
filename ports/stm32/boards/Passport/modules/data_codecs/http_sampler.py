# SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# http_sampler.py
#
# Indicate if the given data is an http URL (very basic!)
#

from .data_sampler import DataSampler


class HttpSampler(DataSampler):
    # Check if the given data looks like a URL
    @classmethod
    def sample(cls, data):
        try:
            result = False
            if isinstance(data, str):
                data = data.lower()
                result = data.startswith('http://') or data.startswith('https://')
            return result
        except Exception as e:
            # Lots of files could contain non-UTF-8 data, so we just ignore these errors as expected
            return False

    # Number of bytes required to successfully recognize this format
    @classmethod
    def min_sample_size(cls):
        return 4
