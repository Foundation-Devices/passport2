# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# sign_electrum_message_flow.py - Sign an electrum standard message via QR

from flows import Flow, ScanQRFlow
from pages import ErrorPage, LongTextPage, QuestionPage, ShowQRPage
from tasks import sign_text_file_task, validate_electrum_message_task
from utils import spinner_task, stylize_address
from data_codecs.qr_type import QRType
import microns
from wallets.utils import get_addr_type_from_deriv
from public_constants import AF_CLASSIC
import stash
from ubinascii import b2a_base64


class SignElectrumMessageFlow(Flow):
    def __init__(self):
        self.message = None
        self.address = None
        self.signature = None
        super().__init__(initial_state=self.scan_message, name='Sign Electrum Message Flow')

    async def scan_message(self):
        result = await ScanQRFlow(qr_types=[QRType.QR],
                                  data_description='a message').run()

        if result is None:
            self.set_result(None)
            return

        self.message = result

        self.goto(self.validate_message)

    async def validate_message(self):
        res = await spinner_task('Validating Message',
                                 validate_electrum_message_task,
                                 args=[self.message])
        (values, error) = res

        if error:
            await ErrorPage(error).show()
            self.set_result(False)
            return

        (self.message, self.subpath) = values

        self.goto(self.show_message)

    async def show_message(self):
        self.addr_format = get_addr_type_from_deriv(self.subpath)

        if self.addr_format is None:
            self.addr_format = AF_CLASSIC

        with stash.SensitiveValues() as sv:
            node = sv.derive_path(self.subpath)
            self.address = sv.chain.address(node, self.addr_format)

        self.address = stylize_address(self.address)

        result = await LongTextPage(centered=True,
                                    text=self.message,
                                    card_header={'title': 'Message'}).show()

        if not result:
            self.set_result(False)
            return

        result = await QuestionPage(text='Sign message with this address?\n\n{}'.format(self.address),
                                    right_micron=microns.Sign).show()

        if not result:
            self.set_result(False)
            return

        self.goto(self.do_sign)

    async def do_sign(self):
        (sig, address, error) = await spinner_task('Signing Message', sign_text_file_task,
                                                   args=[self.message, self.subpath, self.addr_format, True])
        if error is None:
            self.signature = sig
            self.goto(self.show_signed)
        else:
            await ErrorPage(text='Error while signing message: {}'.format(error)).show()
            self.set_result(False)
            return

    async def show_signed(self):
        qr_data = b2a_base64(self.signature).strip().decode()

        result = await ShowQRPage(qr_data=qr_data,
                                  right_micron=microns.Checkmark).show()

        self.set_result(result)
