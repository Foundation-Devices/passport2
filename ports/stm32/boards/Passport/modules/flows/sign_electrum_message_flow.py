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

        print("subpath: {}".format(self.subpath))

        self.goto(self.show_message)

    async def show_message(self):
        from pages import LongTextPage, QuestionPage
        import microns

        result = await LongTextPage(centered=True,
                                    text=self.message,
                                    card_header={'title': 'Message'}).show()

        if not result:
            self.back()
            return

        result = await QuestionPage(text='Sign message with path {}?'.format(self.subpath),
                                    right_micron=microns.Sign).show()

        if not result:
            return

        self.goto(self.do_sign)

    async def do_sign(self):
        from wallets.utils import get_addr_type_from_deriv
        from public_constants import AF_CLASSIC, AF_P2WPKH

        addr_format = get_addr_type_from_deriv(self.subpath)

        if addr_format is None:
            addr_format = AF_CLASSIC

        print('addr_format: {}, AF_P2WPKH: {}, AF_CLASSIC: {}'.format(addr_format, AF_P2WPKH, AF_CLASSIC))

        (signature, address, error) = await spinner_task('Signing Message', sign_text_file_task,
                                                         args=[self.message, self.subpath, addr_format])
        if error is None:
            self.signature = signature
            self.address = address
            self.goto(self.show_signed)
        else:
            # TODO: Refactor this to a simpler, common error handler page?
            await ErrorPage(text='Error while signing message: {}'.format(error)).show()
            self.set_result(False)
            return

    async def show_signed(self):
        from pages import ShowQRPage
        import microns
        from utils import bytes_to_hex_str

        caption = 'Signed by {}'.format(self.address)
        qr_data = bytes_to_hex_str(self.signature)
        print(qr_data)
        print(type(qr_data))

        result = await ShowQRPage(qr_data=qr_data,
                                  right_micron=microns.Checkmark,
                                  caption=caption).show()

        self.set_result(result)
