# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#

import lvgl as lv
from pages import Page
from styles.colors import TEXT_GREY
from styles.style import Stylize
from constants import MENU_ITEM_CORNER_RADIUS
from views import CameraQRScanner, Label
import microns
import common
import passport


def progress_text(p):
    label = 'Scanning...' if p == 0 else '{}%'.format(p)
    return label


class ScanQRPage(Page):
    """Show a page where the user scans a QR with the camera"""

    def __init__(self,
                 card_header=None,
                 statusbar=None,
                 left_micron=microns.Back,
                 right_micron=None,
                 decode_cbor_bytes=False):
        super().__init__(flex_flow=None,
                         card_header=card_header,
                         statusbar=statusbar,
                         left_micron=left_micron,
                         right_micron=right_micron,
                         extend_timeout=True)

        # TODO: Temporary flag until we can cleanup the CBOR handling
        self.decode_cbor_bytes = decode_cbor_bytes
        self.prev_card_header = None
        self.timer = None
        self.camera = CameraQRScanner(result_cb=self.complete,
                                      progress_cb=self.progress,
                                      error_cb=self.error)
        # TODO:
        #   lv.pct(100) just makes the widget inside the camera view to return
        #   invalid values for it's content width.
        #   MOVE THIS CODE SO IT'S CALLED THE FIRST TIME IN update().
        #   THAT WAY, THE lv.pct(100) sizes will work properly.
        #
        #   This size also matches a 6:5 aspect ratio. If the camera resolution
        #   is changed this needs to be updated as well. Also applies in the
        #   lv.pct case. The height needs to be set according to the aspect
        #   ratio and the max width.
        if passport.IS_COLOR:
            self.camera.set_width(212)
            self.camera.set_height(176)
        else:
            # Camera needs to be a square on Founders Edition so that the rotation
            # works properly.
            self.camera.set_width(188)
            self.camera.set_height(188)

        if passport.IS_COLOR:
            self.camera.set_y(-22)
        else:
            self.camera.set_y(-12)
        self.set_scroll_dir(dir=lv.DIR.NONE)
        with Stylize(self.camera) as default:
            default.align(lv.ALIGN.CENTER)
            default.radius(MENU_ITEM_CORNER_RADIUS)
            default.clip_corner(clip=True)

        self.progress_label = Label(text=progress_text(0), color=TEXT_GREY)
        with Stylize(self.progress_label) as default:
            default.align(lv.ALIGN.BOTTOM_MID)
            if passport.IS_COLOR:
                default.pad(bottom=8)
            else:
                # self.progress_label.set_y(0)
                default.pad(bottom=0)

        self.set_children([self.camera, self.progress_label])

    def attach(self, group):
        super().attach(group)
        self.prev_card_header = common.ui.hide_card_header()
        self.camera.attach(group)
        self.timer = lv.timer_create(lambda timer: self.update(), 100, None)

    def detach(self):
        if self.prev_card_header is not None:
            common.ui.set_card_header(**self.prev_card_header, force_all=True)
            self.prev_card_header = None

        if self.timer is not None:
            self.timer._del()  # noqa
            self.timer = None
            self.camera.detach()

        # Unmount camera early
        self.camera.unmount()

        super().detach()

    def update(self):
        if self.is_attached():
            self.camera.update()

    # Just return None.
    def left_action(self, is_pressed):
        if not is_pressed:
            self.set_result(None)

    # Either the user goes back or the scan finishes
    def right_action(self, is_pressed):
        if not is_pressed:
            self.set_result(None)

    def complete(self, qr_decoder):
        self.set_result(QRScanResult(data=qr_decoder.decode(decode_cbor_bytes=self.decode_cbor_bytes),
                                     qr_type=qr_decoder.qr_type()))

    def progress(self, qr_decoder):
        self.progress_label.set_text(progress_text(self.camera.estimated_percent_complete()))

    def error(self, error):
        self.set_result(QRScanResult(error=error))


class QRScanResult:
    """
    QR Code scan result

    Used to distinguish between a QR scan "done" result (either a scan error or valid data),
    and between a cancelled result (`None` returned by ScanQRPage).
    """

    def __init__(self, data=None, error=None, qr_type=None):
        self.data = data
        self.error = error
        self.qr_type = qr_type
