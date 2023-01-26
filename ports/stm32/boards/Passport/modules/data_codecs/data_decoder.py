# SPDX-FileCopyrightText: 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# data_decoder.py
#
# Base class for all data decoders
#


# Collects data segments, indicates when the data is complete, and decodes it to a common
# format for the specified data category
class DataDecoder:
    def __init__(self):
        pass

    # Decode the given data into the expected format
    def add_data(self, data):
        pass

    def received_parts(self):
        return 0

    def total_parts(self):
        return 1

    def is_complete(self):
        return False

    # Return any error message if decoding or adding data failed for some reason
    def get_error(self):
        return None

    def get_ur_prefix(self):
        return None

    def decode(self):
        pass

    # Return what type of QR this is:
    #
    # - Normal QR.
    # - UR2.
    # - etc.
    def qr_type(self):
        pass
