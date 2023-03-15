# SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# qr_factory.py
#
# QR decoders
#

from .qr_codec import QREncoder, QRDecoder, QRSampler
from .ur1_codec import UR1Encoder, UR1Decoder, UR1Sampler
from .ur2_codec import UR2Encoder, UR2Decoder, UR2Sampler
from .compact_seedqr_codec import CompactSeedQREncoder
from .qr_type import QRType

qrs = [
    {'type': QRType.UR2, 'encoder': UR2Encoder, 'decoder': UR2Decoder, 'sampler': UR2Sampler},
    {'type': QRType.UR1, 'encoder': UR1Encoder, 'decoder': UR1Decoder, 'sampler': UR1Sampler},
    {'type': QRType.QR, 'encoder': QREncoder, 'decoder': QRDecoder, 'sampler': QRSampler},
    {'type': QRType.CSQR, 'encoder': CompactSeedQREncoder, 'decoder': None, 'sampler': None},
]


def make_qr_encoder(qr_type):
    for entry in qrs:
        if entry['type'] == qr_type:
            return entry['encoder']()
    return None


def make_qr_decoder_from_data(data):
    """Given a data sample, return its decoder."""

    for entry in qrs:
        if entry['sampler'].sample(data) is True:
            return entry['decoder']()
    return None
