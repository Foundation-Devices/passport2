# SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# psbt_txn_sampler.py
#
# Sampler for PSBT formats
#

from .data_sampler import DataSampler
from ubinascii import hexlify as b2a_hex


class PsbtTxnSampler(DataSampler):
    # Check if the given bytes look like a PSBT.
    # We check binary, hex-encoded and base64-encoded since the PSBT code can handle all those.
    # Return True if it matches or False if not.
    @classmethod
    def sample(cls, data):
        # print('psbt sampler: data={}'.format(b2a_hex(data)))
        if data[0:5] == b'psbt\xff':
            return True
        if data[0:10] == b'70736274ff':        # hex-encoded
            return True
        if data[0:6] == b'cHNidP':             # base64-encoded
            return True

        return False

    # Number of bytes required to successfully recognize this format
    @classmethod
    def min_sample_size(cls):
        return 10
