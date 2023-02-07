# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# casa_health_check_flow.py - Scan and process a Casa health check QR code in `crypto-request` format

from flows import Flow


class CasaHealthCheckCommonFlow(Flow):
    def __init__(self, lines):
        super().__init__(initial_state=self.validate_lines, name='CasaHealthCheckQRFlow')
        self.lines = lines
        self.text = None
        self.subpath = None

    async def validate_lines(self):
        from pages import ErrorPage
        from utils import validate_sign_text
        if len(self.lines) != 2:
            await ErrorPage('Health check format is invalid.').show()
            self.set_result(None)
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
            self.set_result(None)
            return

        self.subpath = subpath
        self.goto(self.sign_health_check)

    async def sign_health_check(self):
        from pages import ErrorPage
        from tasks import sign_text_file_task
        from utils import spinner_task
        from public_constants import AF_CLASSIC
        (signature, address, error) = await spinner_task('Performing Health Check', sign_text_file_task,
                                                         args=[self.text, self.subpath, AF_CLASSIC])
        if error is None:
            self.signature = signature
            self.address = address
            # TODO: do we need save_curr?
            self.goto(self.format_signature, save_curr=False)
        else:
            await ErrorPage(text='Error while signing file: {}'.format(error)).show()
            self.set_result(None)
            return

    async def format_signature(self):
        from ubinascii import b2a_base64
        from public_constants import RFC_SIGNATURE_TEMPLATE

        sig = b2a_base64(self.signature).decode('ascii').strip()

        signed_message = RFC_SIGNATURE_TEMPLATE.format(addr=self.address, msg=self.text, blockchain='BITCOIN', sig=sig)
        self.set_result(signed_message)
