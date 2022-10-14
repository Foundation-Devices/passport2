# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# qrcode.py - Wrapper for LVGL QR code widget

import lvgl as lv
from passport import sram4
from styles.colors import WHITE, BLACK
from .view import View

MAX_QR_VERSION = 13

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
        # TODO: these are returning -8 and 0 when starting the setup process from scratch
        content_width = self.lvgl_root.get_content_width()
        content_height = self.lvgl_root.get_content_height()
        print("content_width: {}, content_height: {}".format(content_width, content_height))
        # TODO: res is not being set
        if content_width > 0 and content_height > 0:
            self.res = min(content_width, content_height)

            # Make the QR Code have a size of the content size.
            self.lvgl_root.set_buffer(sram4.qrcode_buffer,
                                      content_width,
                                      content_height,
                                      sram4.qrcode_modules_buffer,
                                      sram4.MAX_QR_VERSION,
                                      BLACK, WHITE)

    def unmount(self):
        import gc
        super().unmount()
        self.res = None
        gc.collect()

    def reset_sizing(self):
        self.lvgl_root.reset_last_version()

    def get_version_for_data(self, encoded_data):
        enc_len = len(encoded_data)
        for i in range(1, MAX_QR_VERSION + 1):
            if alphanumeric_capacity_by_version[i] >= enc_len:
                return i
        raise QRCodeException()

    def update(self, encoded_data):
        print(encoded_data)
        print("check 1")
        if self.res is None:
            print("check 2")
            self.configure_canvas_buffer()
            if self.res is None:
                print("check 3")
                return

        min_version = self.get_version_for_data(encoded_data)

        last_version = self.lvgl_root.get_last_version()
        print("check 4")

        # Don't go to a smaller QR code, even if it means repeated data since
        # it looks weird to change the QR code size
        if last_version > min_version:
            print("check 5")
            min_version = last_version

        ret = self.lvgl_root.update(encoded_data, len(encoded_data), min_version)
        print("check 6")
        # ret = None
        if ret is lv.RES.INV:
            print("check 7")
            raise QRCodeException()


class QRCodeException(Exception):
    pass
