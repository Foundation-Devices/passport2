# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# camera.py

import lvgl as lv
import foundation
import passport
from foundation import qr
from passport import camera
from views import View
from styles import Stylize
from styles.colors import WHITE
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
        self.img_dsc = None

        if not passport.IS_COLOR and not passport.IS_SIMULATOR:
            with Stylize(self) as default:
                default.bg_color(WHITE)
                default.border_width(0)

    def create_lvgl_root(self, lvgl_parent):  # noqa
        if passport.IS_COLOR or passport.IS_SIMULATOR:
            return lv.img(lvgl_parent)
        else:
            return lv.obj(lvgl_parent)

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
                return

        # Take the camera image.
        camera.snapshot()

        # Hook method, used to convert image to grayscale before giving LVGL
        # full access to the buffer.
        self.hook()

        if passport.IS_COLOR or passport.IS_SIMULATOR:
            # Resize the framebuffer and invalidate the widget contents, so it gets redrawn.
            camera.resize(self.content_width, self.content_height)
            self.lvgl_root.invalidate()
        else:  # MONO device
            # Update the viewfinder using the grayscale image in the QR framebuffer
            import passport_lv
            passport_lv.lcd.update_viewfinder_direct(qr.framebuffer, self.HOR_RES, self.VER_RES)

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

            # Nothing else to do on device since viewfinder is hard-wired at the lower level
            if not passport.IS_COLOR and not passport.IS_SIMULATOR:
                return

            self.lvgl_root.refr_size()

            self.content_width = min(self.content_width, self.HOR_RES)
            self.content_height = min(self.content_height, self.VER_RES)
            self.img_dsc = lv.img_dsc_t({
                'header': {
                    'cf': lv.img.CF.TRUE_COLOR,
                    'w': self.content_width,
                    'h': self.content_height,
                },
                'data': self._framebuffer,
            })
            self.lvgl_root.set_src(self.img_dsc)
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

    def __init__(self):
        super().__init__()
        self.qr_decoder = None
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

        # Do not scan anything if decoding is complete.
        if self.qr_decoder is not None:
            if self.qr_decoder.is_complete():
                return

        # Find QR codes in the QR framebuffer, and return early if no data found.
        data = qr.scan()
        if data is None:
            return

        if self.qr_decoder is None:
            self.qr_decoder = get_qr_decoder_for_data(data)

        self.qr_decoder.add_data(data)

    def estimated_percent_complete(self):
        """Returns an integer from 0-100 representing the estimated percentage of completion"""

        if self.qr_decoder is None:
            return 0

        return self.qr_decoder.estimated_percent_complete()

    def is_complete(self):
        """Returns true if the scan is complete"""

        if self.qr_decoder is not None:
            return self.qr_decoder.is_complete()
        return False
