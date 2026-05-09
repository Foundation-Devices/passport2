# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# health_check_flow.py - Scan and process a health check QR code in `crypto-request` format

from flows import Flow
from data_codecs.qr_type import QRType
from foundation import ur


class HealthCheckQRFlow(Flow):
    def __init__(self, context=None):
        super().__init__(initial_state=self.scan_qr, name='HealthCheckQRFlow')

        self.service_name = context
        self.lines = None
        self.signed_message = None

    async def scan_qr(self):
        from pages import ErrorPage
        from flows import ScanQRFlow

        data_description = 'a {} health check'.format(self.service_name)
        result = await ScanQRFlow(qr_types=[QRType.UR2],
                                  ur_types=[ur.Value.BYTES],
                                  data_description=data_description).run()
        if result is None:
            self.set_result(False)
            return

        try:
            data = result.unwrap_bytes().decode('utf-8')
            self.lines = data.split('\n')
        except Exception as e:
            await ErrorPage('Health check format is invalid.').show()
            self.set_result(False)
            return

        self.goto(self.common_flow)

    async def common_flow(self):
        from flows import HealthCheckCommonFlow

        self.signed_message = await HealthCheckCommonFlow(self.lines).run()
        if self.signed_message is None:
            self.set_result(False)
            return
        self.goto(self.show_signed_message)

    async def show_signed_message(self):
        from pages import ShowQRPage

        result = await ShowQRPage(
            qr_type=QRType.UR2,
            qr_data=ur.new_bytes(self.signed_message),
            caption='Signed Health Check'
        ).show()
        if not result:
            self.back()
        else:
            self.set_result(True)
