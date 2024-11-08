# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# system_test_camera_flow.py - Scans a QR code with the camera and shows the data in it

from flows import Flow, ScanQRFlow
from pages import SuccessPage, QuestionPage
from foundation import ur


class TestCameraFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.scan_qr, name='TestCameraFlow')

    async def scan_qr(self):
        result = await ScanQRFlow(data_description='a normal QR code').run()
        if result is None:
            skip = await QuestionPage(text='Skip the Camera test?').show()
            self.set_result(skip)
        else:
            await SuccessPage(result).show()
            self.set_result(True)
