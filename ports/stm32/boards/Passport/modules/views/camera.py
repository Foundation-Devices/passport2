# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# camera.py

import lvgl as lv
import foundation
from foundation import qr
from passport import camera
from views import View
from data_codecs.qr_factory import get_qr_decoder_for_data


class Camera(View):
    """
    Camera component

    This uses the Passport built-in camera to display a scaled version of the
    camera image on the screen.

    On the color screens the framebuffer is shared with the camera, so when the
    camera component is created the display driver is re-assigned a new draw
    buffer with a smaller memory, in order for both buffers to co-exist. When
    the camera is disabled with the display driver is also updated to start
    using again the full sized buffer.

    Keep this in mind when using animations with the camera component.

    When running on the simulator, the display driver is not changed.
    The camera framebuffer is used directly with the LVGL canvas.
    """

    HOR_RES = camera.HOR_RES
    VER_RES = camera.VER_RES

    def __init__(self):
        """Initialize the camera component"""
        super().__init__()
        self._framebuffer = None
        self.content_width = None
        self.content_height = None

    def create_lvgl_root(self, lvgl_parent):  # noqa
        return lv.canvas(lvgl_parent)

    def hook(self):
        pass

    def detach(self):
        self.disable()
        super().detach()

    def update(self):
        """Take a camera snapshot and render it"""

        if not self.is_mounted():
            return

        # Enable the camera only when the widget has a proper size.
        if self.content_width is None or self.content_height is None:
            self.enable()
            if self.content_width is None or self.content_height is None:
                print('Not enabled')
                return
        print('{}x{}'.format(self.content_width, self.content_height))

        # Take the camera image.
        camera.snapshot()

        # Hook method, used to convert image to grayscale before giving LVGL
        # full access to the buffer.
        self.hook()

        # Resize the framebuffer and invalidate the widget contents, so it gets redrawn.
        camera.resize(self.content_width, self.content_height)
        self.lvgl_root.invalidate()

    def enable(self):
        """Enable the camera"""
        assert self.is_mounted()

        self.content_width = self.lvgl_root.get_content_width()
        self.content_height = self.lvgl_root.get_content_height()
        if self.content_width > 0 and self.content_height > 0:
            # Turn on the camera. This is where the display driver is updated.
            camera.enable()

            # Set the canvas "drawing buffer" directly to the camera framebuffer,
            # in order to tell LVGL when a frame has been updated we use a task and
            # the lv.obj().invalidate() method to tell LVGL to redraw it (the
            # complete area). The pixel format of the camera is the same one as the
            # LVGL format.
            self._framebuffer = camera.framebuffer()
            self.lvgl_root.refr_size()
            self.content_width = min(self.content_width, self.HOR_RES)
            self.content_height = min(self.content_height, self.VER_RES)
            self.lvgl_root.set_buffer(self._framebuffer,
                                      self.content_width,
                                      self.content_height,
                                      lv.img.CF.TRUE_COLOR)
        else:
            self.content_width = None
            self.content_height = None


    def disable(self):
        """Disable the camera"""

        # assert self.is_mounted()

        self._framebuffer = None
        camera.disable()

    def framebuffer(self):
        return self._framebuffer


class CameraQRScanner(Camera):
    """Camera QR code scanner and decoder"""

    def __init__(self, result_cb=None, progress_cb=None, error_cb=None):
        super().__init__()
        self.qr_decoder = None
        self.result_cb = result_cb
        self.progress_cb = progress_cb
        self.error_cb = error_cb
        qr.init(self.HOR_RES, self.VER_RES)

    def hook(self):
        # Convert RGB565 framebuffer to a grayscale framebuffer.
        foundation.convert_rgb565_to_grayscale(self.framebuffer(),
                                               qr.framebuffer,
                                               self.HOR_RES,
                                               self.VER_RES)

    def detach(self):
        self.qr_decoder = None
        super().detach()

    def update(self):
        """Update view and scan QR codes in the frame"""

        super().update()

        # print('update')

        # Do not scan anything if we are completed decoding.
        if self.qr_decoder is not None:
            if self.qr_decoder.is_complete():
                return

        # print('decoding')

        # Find QR codes in the QR framebuffer, and return early if no data found.
        data = qr.scan()

        if data is None:
            # print('None')
            return

        # print('============================================================')
        # print('data {}'.format(data))
        # print('============================================================')

        try:
            if self.qr_decoder is None:
                self.qr_decoder = get_qr_decoder_for_data(data)

            self.qr_decoder.add_data(data)

            error = self.qr_decoder.get_error()
            if error is not None:
                if callable(self.error_cb):
                    self.error_cb(error)
                return

            if self.qr_decoder.is_complete():
                if callable(self.result_cb):
                    self.result_cb(self.qr_decoder)
                return

            if callable(self.progress_cb):
                self.progress_cb(self.qr_decoder)
        except Exception as e:  # noqa
            # print('Exception in CameraQRScanner: {}'.format(e))
            pass
