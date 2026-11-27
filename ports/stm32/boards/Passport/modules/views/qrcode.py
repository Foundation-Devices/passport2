# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# qrcode.py - Wrapper for LVGL QR code widget

import lvgl as lv
from passport import mem
from styles.colors import WHITE, BLACK
from .view import View

# Capacity in bytes for LOW ECC and alphanumeric
alphanumeric_capacity_by_version = [
    0,
    25,
    47,
    77,
    114,
    154,
    195,
    224,
    279,
    335,
    339,
    468,
    535,
    619
]

# Capacity in bytes for LOW ECC and numeric
numeric_capacity_by_version = [
    0,
    41,
    77,
    127,
    187,
    255,
    322,
    370,
    461,
    552,
    652,
    772,
    883,
    1022
]


class QRCode(View):
    """Displays a QR code"""

    def __init__(self):
        """
        Initialize the QR code view.

        The vertical resolution and horizontal resolution don't take into
        account the parent widget size.

        The user of this view must take that into account and select the
        appropriate size for the QR code.
        """

        super().__init__()
        self.res = None

    def create_lvgl_root(self, lvgl_parent):
        return lv.qrcode(lvgl_parent)

    def configure_canvas_buffer(self):
        content_width = self.lvgl_root.get_content_width()
        content_height = self.lvgl_root.get_content_height()
        if content_width > 0 and content_height > 0:
            self.res = min(content_width, content_height)

            # Make the QR Code have a size of the content size.
            self.lvgl_root.set_buffer(mem.qrcode_buffer,
                                      content_width,
                                      content_height,
                                      mem.qrcode_modules_buffer,
                                      mem.MAX_QR_VERSION,
                                      BLACK, WHITE)

    def unmount(self):
        import gc
        super().unmount()
        self.res = None
        gc.collect()

    def reset_sizing(self):
        self.lvgl_root.reset_last_version()

    def get_version_for_data(self, encoded_data, qr_type):
        from data_codecs.qr_type import QRType

        enc_len = len(encoded_data)
        if qr_type in [QRType.COMPACT_SEED_QR, QRType.SEED_QR]:
            capacity_by_version = numeric_capacity_by_version
        else:
            capacity_by_version = alphanumeric_capacity_by_version
        for i in range(1, mem.MAX_QR_VERSION + 1):
            if capacity_by_version[i] >= enc_len:
                return i
        raise QRCodeException("Cannot fit {} in a QR code ({} bytes)".format(encoded_data, len(encoded_data)))

    def update(self, encoded_data, qr_type):
        if self.res is None:
            self.configure_canvas_buffer()
            if self.res is None:
                return

        min_version = self.get_version_for_data(encoded_data, qr_type)

        last_version = self.lvgl_root.get_last_version()

        # Don't go to a smaller QR code, even if it means repeated data since
        # it looks weird to change the QR code size
        if last_version > min_version:
            min_version = last_version

        ret = self.lvgl_root.update(encoded_data, len(encoded_data), min_version)
        if ret is lv.RES.INV:
            raise QRCodeException()


class QRCodeException(Exception):
    pass
