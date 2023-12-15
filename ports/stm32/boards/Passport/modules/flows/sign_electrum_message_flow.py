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
        self.address = None
        self.signature = None
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

        # msg = uio.StringIO(self.message)
        # header = msg.readline()
        # self.message = self.message[len(header)::]

        # header_elements = header.split(' ')

        parts = self.message.split(':', 1)
        self.message = parts[1]
        header_elements = parts[0].split(' ')

        if len(header_elements) != 3:
            await ErrorPage('Message format must be "signmessage {derivation_path} ascii:{message}"').show()
            self.set_result(False)

        print("header:")
        print(header_elements)
        print("message:")
        print(self.message)

        if header_elements[0] != 'signmessage':
            await ErrorPage('Not a valid message to sign').show()
            self.set_result(False)
            return

        if header_elements[2] != 'ascii':
            await ErrorPage('Unsupported message type').show()
            self.set_result(False)
            return

        (self.subpath, error) = validate_sign_text(self.message,
                                                   header_elements[1],
                                                   space_limit=False,
                                                   check_whitespace=False)

        if error:
            await ErrorPage(error).show()
            self.set_result(False)
            return

        print("subpath: {}".format(self.subpath))

        self.goto(self.show_message)

    async def show_message(self):
        from pages import LongTextPage, QuestionPage
        import microns
        from wallets.utils import get_addr_type_from_deriv
        from public_constants import AF_CLASSIC, AF_P2WPKH
        import stash
        from utils import stylize_address

        result = await LongTextPage(centered=True,
                                    text=self.message,
                                    card_header={'title': 'Message'}).show()

        self.address

        if not result:
            self.set_result(False)
            return

        self.addr_format = get_addr_type_from_deriv(self.subpath)

        if self.addr_format is None:
            self.addr_format = AF_CLASSIC

        print('addr_format: {}, AF_P2WPKH: {}, AF_CLASSIC: {}'.format(self.addr_format, AF_P2WPKH, AF_CLASSIC))

        with stash.SensitiveValues() as sv:
            node = sv.derive_path(self.subpath)
            self.address = sv.chain.address(node, self.addr_format)

        self.address = stylize_address(self.address)

        result = await QuestionPage(text='Sign message with this address?\n\n{}'.format(self.address),
                                    right_micron=microns.Sign).show()

        if not result:
            self.set_result(False)
            return

        self.goto(self.do_sign)

    async def do_sign(self):
        (signature, address, error) = await spinner_task('Signing Message', sign_text_file_task,
                                                         args=[self.message, self.subpath, self.addr_format])

        if error is None:
            self.signature = signature
            self.goto(self.show_signed)
        else:
            # TODO: Refactor this to a simpler, common error handler page?
            await ErrorPage(text='Error while signing message: {}'.format(error)).show()
            self.set_result(False)
            return

    async def show_signed(self):
        from pages import ShowQRPage
        import microns
        from ubinascii import b2a_base64

        qr_data = b2a_base64(self.signature)
        print(qr_data)
        print(type(qr_data))

        result = await ShowQRPage(qr_data=qr_data,
                                  right_micron=microns.Checkmark).show()

        self.set_result(result)
