# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# sign_electrum_message_flow.py - Sign an electrum standard message via QR

from flows import Flow
from pages import SuccessPage, ErrorPage, InsertMicroSDPage
from tasks import sign_text_file_task
from utils import spinner_task, validate_sign_text
from translations import t, T
from public_constants import AF_CLASSIC, MSG_SIGNING_MAX_LENGTH, RFC_SIGNATURE_TEMPLATE
import sys


class SignElectrumMessageFlow(Flow):
    def __init__(self):
        self.message = None
        super().__init__(initial_state=self.scan_message, name='Sign Electrum Message Flow')

    async def scan_message(self):
        from flows import ScanQRFlow
        from data_codecs.qr_type import QRType

        result = await ScanQRFlow(qr_types=[QRType.QR],
                                  data_description='a message').run()

        if result is None:
            self.set_result(None)
            return

        self.message = result

        self.goto(self.validate_message)

    async def validate_message(self):
        import uio
        from pages import ErrorPage
        from utils import validate_sign_text

        msg = uio.StringIO(self.message)
        header = msg.readline()
        self.message = self.message[len(header)::]

        print("header:")
        print(header)
        print("message:")
        print(self.message)

        header_elements = header.split(' ')

        if header_elements[0] != 'signmessage':
            await ErrorPage('Not a valid message to sign').show()
            self.set_result(False)
            return

        if header_elements[2] != 'ascii:\n':
            await ErrorPage('Unsupported message type').show()
            self.set_result(False)
            return

        (self.subpath, error) = validate_sign_text(self.message, header_elements[1], space_limit=False)

        if error:
            await ErrorPage(error).show()
            self.set_result(False)
            return

        await ErrorPage('What now?').show()
        self.set_result(True)

    async def do_sign(self):
        (signature, address, error) = await spinner_task('Signing File', sign_text_file_task,
                                                         args=[self.text, self.subpath, AF_CLASSIC])
        if error is None:
            self.signature = signature
            self.address = address
            self.goto(self.write_signed_file)
        else:
            # TODO: Refactor this to a simpler, common error handler page?
            await ErrorPage(text='Error while signing file: {}'.format(error)).show()
            self.set_result(False)
            return

    async def write_signed_file(self):
        # complete. write out result
        from ubinascii import b2a_base64
        from flows import SaveToMicroSDFlow
        from public_constants import RFC_SIGNATURE_TEMPLATE

        orig_path, basename = self.file_path.rsplit('/', 1)
        base, ext = basename.rsplit('.', 1)
        filename = base + '-signed' + '.' + ext
        sig = b2a_base64(self.signature).decode('ascii').strip()
        data = RFC_SIGNATURE_TEMPLATE.format(addr=self.address, msg=self.text, blockchain='BITCOIN', sig=sig)
        result = await SaveToMicroSDFlow(filename=filename,
                                         data=data,
                                         success_text="signed file",
                                         path=orig_path,
                                         mode='t').run()
        self.set_result(result)
