# SPDX-FileCopyrightText: 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# data_decoder.py
#
# Base class for all data decoders
#


# Collects data segments, indicates when the data is complete, and decodes it to a common
# format for the specified data category
class DataEncoder:
    def __init__(self):
        pass

    def encode(self, data, is_binary=False, max_fragment_len=None):
        pass

    def next_part(self):
        return None

    # Return any error message if decoding or adding data failed for some reason
    def get_error(self):
        return None
