# SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# ur1_sampler.py
#
# UR 1.0 codec
#

from .data_encoder import DataEncoder
from .data_decoder import DataDecoder, DecodeError
from .data_sampler import DataSampler
from .qr_type import QRType

_BC32_CHARSET = 'qpzry9x8gf2tvdw0s3jn54khce6mua7l'


class UR1Decoder(DataDecoder):
    def __init__(self):
        raise DecodeError('''Unsupported format.

The QR code scanned uses UR1 and it is not supported as it has been \
superseded by UR2.
''')

    def qr_type(self):
        return QRType.UR1


class UR1Encoder(DataEncoder):
    pass


class UR1Sampler(DataSampler):
    # Check if the given bytes look like UR1 data
    # Return True if it matches or False if not
    @classmethod
    def sample(cls, data):
        data = data.lower()

        if not data.startswith('ur:'):
            return False

        pieces = data.split('/')
        if not (2 <= len(pieces) <= 4):
            return False

        # UR1 and UR2 can have a somewhat similar URI format but the BC32
        # vs bytewords encoding differentiates them.
        fragment = pieces[-1]
        for i in range(len(fragment)):
            if _BC32_CHARSET.find(fragment[i]) == -1:
                return False

        return True

    # Number of bytes required to successfully recognize this format
    @classmethod
    def min_sample_size(cls):
        return 20
