# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# system_test_camera_flow.py - Scans a QR code with the camera and shows the data in it

from flows import Flow
import microns
from pages import ScanQRPage
from pages import ErrorPage, SuccessPage, QuestionPage


class TestCameraFlow(Flow):
    def __init__(self, card_header=None, statusbar=None):
        super().__init__(initial_state=self.scan_qr, name='TestQrScanFlow')
        self.card_header = card_header
        self.statusbar = statusbar

    async def scan_qr(self):
        result = await ScanQRPage(
            card_header=self.card_header, statusbar=self.statusbar, right_micron=microns.Cancel).show()
        if result is None:
            skip = await QuestionPage(text='Skip the Camera test?').show()
            self.set_result(skip)
        else:
            # Got a scan result (aka QRScanResult): good data or error
            if result.is_failure():
                # Unable to scan QR code - show error?
                await ErrorPage(text='Unable to scan QR code.').show()
                self.set_result(False)
            else:
                data = result.data
                await SuccessPage(data).show()
                self.set_result(True)
