# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# health_check_flow.py - Scan and process a health check QR code in `crypto-request` format

from flows import Flow
from pages import ErrorPage, SuccessPage
from pages.show_qr_page import ShowQRPage
from utils import validate_sign_text, spinner_task
from tasks import sign_text_file_task
from public_constants import AF_CLASSIC, RFC_SIGNATURE_TEMPLATE
from data_codecs.qr_type import QRType
from foundation import ur


class HealthCheckQRFlow(Flow):
    def __init__(self, context=None):
        super().__init__(initial_state=self.scan_qr, name='HealthCheckQRFlow')

        self.service_name = context
        self.text = None
        self.subpath = None

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
            lines = data.split('\n')
            if len(lines) != 2:
                await ErrorPage('Health check format is invalid.').show()
                self.set_result(False)
                return

            self.text = lines[0]
            self.subpath = lines[1]
        except Exception as e:
            await ErrorPage('Health check format is invalid.').show()
            self.set_result(False)
            return

        # Validate
        (subpath, error) = validate_sign_text(self.text, self.subpath)
        if error is not None:
            await ErrorPage(text=error).show()
            self.set_result(False)
            return

        self.subpath = subpath
        self.goto(self.sign_health_check)

    async def sign_health_check(self):
        (signature, address, error) = await spinner_task('Performing Health Check',
                                                         sign_text_file_task,
                                                         args=[self.text, self.subpath, AF_CLASSIC])
        if error is None:
            self.signature = signature
            self.address = address
            self.goto(self.show_signed_message, save_curr=False)
        else:
            await ErrorPage(text='Error while signing file: {}'.format(error)).show()
            self.set_result(False)
            return

    async def show_signed_message(self):
        from ubinascii import b2a_base64

        sig = b2a_base64(self.signature).decode('ascii').strip()

        signed_message = ur.new_bytes(RFC_SIGNATURE_TEMPLATE.format(addr=self.address,
                                                                    msg=self.text,
                                                                    blockchain='BITCOIN',
                                                                    sig=sig))

        result = await ShowQRPage(
            qr_type=QRType.UR2,
            qr_data=signed_message,
            caption='Signed Health Check'
        ).show()
        if not result:
            self.back()
        else:
            self.set_result(True)
