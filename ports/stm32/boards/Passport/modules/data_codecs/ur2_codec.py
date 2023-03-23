# SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# ur2_codec.py
#
# UR 2.0 Codec
#
import math
import re

from .data_encoder import DataEncoder
from .data_decoder import DataDecoder, DecodeError
from .data_sampler import DataSampler
from .qr_type import QRType

from foundation import ur


class UR2Decoder(DataDecoder):
    def __init__(self):
        ur.decoder_clear()
        self.value = None

    def add_data(self, data):
        data = data.lower()

        try:
            ur.decoder_receive(data)
        except ur.NotMultiPartError as exc:
            if ur.decoder_is_empty():
                try:
                    self.value = ur.decode_single_part(data)
                except ur.UnsupportedError as exc:
                    raise DecodeError("Unsupported UR.\n\n{}".format(str(exc)))
                except ur.OtherError as exc:
                    raise DecodeError(str(exc))
            else:
                raise DecodeError("""\
Received single-part UR when multi-part reception was already in place""")
        except ur.UnsupportedError as exc:
            raise DecodeError("Unsupported UR.\n\n{}".format(str(exc)))
        except ur.OtherError as exc:
            raise DecodeError(str(exc))

    def estimated_percent_complete(self):
        if self.value is not None:
            return 100

        return ur.decoder_estimated_percent_complete()

    def is_complete(self):
        if self.value is not None:
            return True

        return ur.decoder_is_complete()

    def decode(self):
        try:
            if self.value is None:
                self.value = ur.decoder_decode_message()
        except ur.Other as exc:
            raise DecodeError(str(exc))
        except ur.Unsupported as exc:
            raise DecodeError("Unsupported UR.\n\n{}".format(str(exc)))
        finally:
            return self.value

    def qr_type(self):
        return QRType.UR2


class UR2Encoder(DataEncoder):
    def encode(self, value, max_fragment_len=200):
        """Initialize the encoder using the given UR data value"""

        ur.encoder_start(value, max_fragment_len)

    def next_part(self):
        """Returns the next part of the UR encoder"""

        return ur.encoder_next_part()


class UR2Sampler(DataSampler):
    @classmethod
    def sample(cls, data):
        """
        Check if the given bytes look like UR2 data

        :param bytes data: The bytes to check.
        :return: True if it matches or False if not.
        """

        return ur.validate(data.lower())

    @classmethod
    def min_sample_size(cls):
        """Number of bytes required to successfully recognize this format."""
        return 20
