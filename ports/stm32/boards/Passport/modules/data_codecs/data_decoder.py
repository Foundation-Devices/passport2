# SPDX-FileCopyrightText: 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# data_decoder.py
#
# Base class for all data decoders
#


class DecodeError(Exception):
    pass


# Collects data segments, indicates when the data is complete, and decodes it to a common
# format for the specified data category
class DataDecoder:
    def __init__(self):
        pass

    # Decode the given data into the expected format
    def add_data(self, data):
        pass

    def estimated_percent_complete(self):
        return 0

    def is_complete(self):
        return False

    def decode(self):
        pass

    # Return what type of QR this is:
    #
    # - Normal QR.
    # - UR2.
    # - etc.
    def qr_type(self):
        pass
