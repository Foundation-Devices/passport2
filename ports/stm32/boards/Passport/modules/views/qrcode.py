# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#

import lvgl as lv
import foundation
from passport import sram4
from styles.colors import WHITE, BLACK
from .view import View


class QRCode(View):
    """Displays a QR code"""

    def __init__(self, encoded_data=None):
        """
        Initialize the QR code view.

        The vertical resolution and horizontal resolution don't take into
        account the parent widget size.

        The user of this view must take that into account and select the
        appropriate size for the QR code.

        :param encoded_data: The initial QR code data to display.
        """
        super().__init__()
        self.encoded_data = encoded_data
        self.qrcode = foundation.QRCode()
        self.last_version = 1
        self.modules_count = None
        self.qr_data = None
        self.res = None

    def create_lvgl_root(self, lvgl_parent):
        return lv.canvas(lvgl_parent)

    def configure_canvas_buffer(self):
        content_width = self.lvgl_root.get_content_width()
        content_height = self.lvgl_root.get_content_height()
        if content_width > 0 and content_height > 0:
            self.res = min(content_width, content_height)

            # Make the image have a size of the content size.  Later we center the
            # QR code inside the image itself.
            self.lvgl_root.set_buffer(sram4.qrcode_buffer,
                                      content_width,
                                      content_height,
                                      lv.img.CF.INDEXED_1BIT)
            self.lvgl_root.set_palette(0, WHITE)
            self.lvgl_root.set_palette(1, BLACK)

    def unmount(self):
        import gc
        super().unmount()
        self.res = None
        gc.collect()

    def attach(self, group):
        super().attach(group)
        sram4.qrcode_buffer_clear()

        # # The QR code resolution will be the minimum of the horizontal and
        # # vertical resolution, to avoid overflowing the "view".
        # content_width = 150  # self.lvgl_root.get_content_width()
        # content_height = 150  # self.lvgl_root.get_content_height()
        # print('content_width={}, content_height={}'.format(content_width, content_height))
        # self.res = min(content_width, content_height)

    def detach(self):
        super().detach()

    def reset_sizing(self):
        self.last_version = 1

    def render(self):
        version = self.qrcode.fit_to_version(len(self.encoded_data),
                                             _is_alphanumeric_qr(self.encoded_data))

        # print('version={} len(encoded_data)={}'.format(version, len(self.encoded_data)))

        # Don't go to a smaller QR code, even if it means repeated data since
        # it looks weird to change the QR code size
        if self.last_version > version:
            version = self.last_version
        else:
            self.last_version = version

        if version > sram4.MAX_QR_VERSION:
            raise QRCodeException()

        ret = self.qrcode.render(self.encoded_data, version, 0, sram4.qrcode_modules_buffer)
        if not ret:
            raise QRCodeException()

        self.qr_data = sram4.qrcode_modules_buffer
        # print('version={}'.format(version))
        self.modules_count = _qr_get_module_size_for_version(version)

    def redraw(self):
        sram4.qrcode_buffer_clear()

        module_pixel_width = self.res // self.modules_count
        total_pixel_width = self.modules_count * module_pixel_width
        x0 = (self.lvgl_root.get_content_width() - total_pixel_width) // 2
        y0 = (self.lvgl_root.get_content_height() - total_pixel_width) // 2

        if self.qr_data is not None:
            c = lv.color_t()
            for qy in range(self.modules_count):
                for qx in range(self.modules_count):
                    offset = qy * self.modules_count + qx
                    px = (self.qr_data[offset >> 3]) & (1 << (7 - (offset & 0x07)))

                    if px == 0:
                        c.full = 0
                    else:
                        c.full = 1

                    module_x = x0 + (qx * module_pixel_width)
                    module_y = y0 + (qy * module_pixel_width)
                    self._fill_module(module_x, module_y, module_pixel_width, c)

        self.lvgl_root.invalidate()

    def update(self, encoded_data):
        self.encoded_data = encoded_data

        if self.res is None:
            self.configure_canvas_buffer()
            if self.res is None:
                return

        self.render()
        self.redraw()

    def _fill_module(self, x, y, w, c):
        for qy in range(w):
            for qx in range(w):
                self.lvgl_root.set_px_color(x + qx, y + qy, c)


class QRCodeException(Exception):
    pass


_ALPHANUMERIC_CHARS = {
    '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
    'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
    'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z',
    ' ', '$', '%', '*', '+', '-', '.', '/', ':'
}


def _is_char_alphanumeric(ch):
    return ch in _ALPHANUMERIC_CHARS


def _is_alphanumeric_qr(buf):
    """
    Alphanumeric QR codes contain only the following characters:

    0–9, A–Z (upper-case only), space, $, %, *, +, -, ., /, :

    :param buf: The QR data to check.
    :return: true if alphanumeric, false otherwise.
    """

    for ch in buf:
        is_alpha = _is_char_alphanumeric(chr(ch))
        if not is_alpha:
            return False

    return True


def _qr_get_module_size_for_version(version):
    """
    Get QR code version module size.

    - 1 -> 21
    - 2 -> 25
    - etc.

    :param version: QR code version.
    :return: QR code module size.
    """

    return version * 4 + 17
