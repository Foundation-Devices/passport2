# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# casa_health_check_flow.py - Scan and process a Casa health check QR code in `crypto-request` format

from flows import Flow
from pages import ErrorPage, SuccessPage
from pages.show_qr_page import ShowQRPage
from utils import validate_sign_text, spinner_task
from tasks import sign_text_file_task
from public_constants import AF_CLASSIC, RFC_SIGNATURE_TEMPLATE
from data_codecs.qr_type import QRType
from foundation import ur


class CasaHealthCheckQRFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.scan_qr, name='CasaHealthCheckQRFlow')
        self.lines = None

    async def scan_qr(self):
        from pages import ScanQRPage, ErrorPage
        import microns

        result = await ScanQRPage(right_micron=microns.Checkmark).show()

        if result is None:
            # User canceled the scan
            self.set_result(False)
        else:
            # Got a scan result (aka QRScanResult).
            if result.is_failure():
                await ErrorPage(text='Unable to scan QR code.\n\n{}'.format(result.error)).show()
                self.set_result(False)
            else:
                if not isinstance(result.data, ur.Value):
                    await ErrorPage(text='Unable to scan QR code.\n\nNot a Uniform Resource.').show()
                    self.set_result(False)
                    return

                try:
                    data = result.data.unwrap_bytes()
                    self.lines = data.decode('utf-8').split('\n')
                except Exception as e:
                    await ErrorPage('Health check format is invalid.').show()
                    return
                if len(self.lines) != 2:
                    await ErrorPage('Health check format is invalid.').show()
                    self.set_result(False)
                    return

                # Common function to validate the message
                self.text = self.lines[0]
                self.subpath = self.lines[1]
                # print('text={}'.format(self.text))
                # print('subpath={}'.format(self.subpath))

                # Validate
                (subpath, error) = validate_sign_text(self.text, self.subpath)
                if error is not None:
                    await ErrorPage(text=error).show()
                    self.set_result(False)
                    return

                self.subpath = subpath

                self.goto(self.sign_health_check)

    async def sign_health_check(self):
        (signature, address, error) = await spinner_task('Performing Health Check', sign_text_file_task,
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

        signed_message = RFC_SIGNATURE_TEMPLATE.format(addr=self.address, msg=self.text, blockchain='BITCOIN', sig=sig)

        result = await ShowQRPage(
            qr_type=QRType.UR2,
            qr_data=signed_message,
            caption='Signed Health Check'
        ).show()
        if not result:
            self.back()
        else:
            self.set_result(True)
