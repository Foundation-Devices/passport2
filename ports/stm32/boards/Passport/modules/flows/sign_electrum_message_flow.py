# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# sign_electrum_message_flow.py - Sign an electrum standard message via QR

import lvgl as lv
from flows import Flow, ScanQRFlow, FilePickerFlow, ReadFileFlow, SaveToMicroSDFlow
from pages import ErrorPage, LongTextPage, LongQuestionPage, ShowQRPage, ChooserPage
from tasks import sign_text_file_task, validate_electrum_message_task
from utils import spinner_task, stylize_address
from data_codecs.qr_type import QRType
import microns
from wallets.utils import get_addr_type_from_deriv
from public_constants import AF_CLASSIC, MARGIN_FOR_ADDRESSES
import stash
from ubinascii import b2a_base64


class SignElectrumMessageFlow(Flow):
    def __init__(self):
        self.message = None
        self.address = None
        self.signature = None
        self.qr_flow = True
        self.file_path = None
        self.filename = None

        super().__init__(initial_state=self.choose_mode, name='Sign Electrum Message Flow')

    async def choose_mode(self):

        text = '\nHow would you like to sign your message?'
        options = [{'label': 'QR Code', 'value': True},
                   {'label': 'microSD', 'value': False}]

        result = await ChooserPage(text=text, options=options).show()
        if result is None:
            self.set_result(False)
            return

        self.qr_flow = result
        if self.qr_flow:
            self.goto(self.scan_message)
        else:
            self.goto(self.choose_file)

    async def choose_file(self):
        result = await FilePickerFlow(show_folders=True).run()

        if result is None:
            self.back()
            return

        filename, full_path, is_folder = result
        if not is_folder:
            self.file_path = full_path
            self.filename = filename

        self.goto(self.read_file)

    async def read_file(self):
        message = await ReadFileFlow(self.file_path, binary=False).run()

        if not message:
            await ErrorPage("Failed to read {}. Make sure it contains a message.".format(self.filename))
            self.back()
            return

        self.message = message
        self.goto(self.validate_message)

    async def scan_message(self):
        result = await ScanQRFlow(qr_types=[QRType.QR],
                                  data_description='a message').run()

        if result is None:
            self.back()
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
                                    text=('\n' + self.message),
                                    card_header={'title': 'Message'}).show()

        if not result:
            self.set_result(False)
            return

        result = await LongQuestionPage(text='Sign message with this address?\n\n{}'.format(self.address),
                                        right_micron=microns.Sign,
                                        margins=MARGIN_FOR_ADDRESSES,
                                        top_margin=8).show()

        if not result:
            self.set_result(False)
            return

        self.goto(self.do_sign)

    async def do_sign(self):
        (sig, address, error) = await spinner_task('Signing Message', sign_text_file_task,
                                                   args=[self.message, self.subpath, self.addr_format, True])
        if error:
            await ErrorPage(text='Error while signing message: {}'.format(error)).show()
            self.set_result(False)
            return

        self.signature = b2a_base64(sig).strip().decode()
        if self.qr_flow:
            self.goto(self.show_signed)
        else:
            self.goto(self.save_signed)

    async def show_signed(self):
        result = await ShowQRPage(qr_data=self.signature,
                                  right_micron=microns.Checkmark).show()

        self.set_result(result)

    async def save_signed(self):
        orig_path, basename = self.file_path.rsplit('/', 1)

        # Some users may save their message file without an extension
        if basename.find('.') == -1:
            base = basename
            ext = 'txt'
        else:
            base, ext = basename.rsplit('.', 1)

        filename = base + '-signed' + '.' + ext
        result = await SaveToMicroSDFlow(filename=filename,
                                         data=self.signature,
                                         success_text="signed message",
                                         path=orig_path).run()
        self.set_result(result)
