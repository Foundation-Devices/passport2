# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# sign_electrum_message_flow.py - Sign a message via QR, sent as text or as a BIP-322 request in a PSBT

from flows import Flow, ScanQRFlow
from pages import ErrorPage, LongTextPage, LongQuestionPage, ShowQRPage
from tasks import sign_text_file_task, validate_bip322_request_task, validate_electrum_message_task
from utils import escape_text, message_review_warning, spinner_task, stylize_address
from data_codecs.qr_type import QRType
from foundation import ur
import microns
from wallets.utils import get_addr_type_from_deriv
from public_constants import AF_CLASSIC, MARGIN_FOR_ADDRESSES
import stash


class SignElectrumMessageFlow(Flow):
    def __init__(self):
        self.message = None
        self.address = None
        self.signature = None
        self.psbt = None
        self.bip322_request = None
        super().__init__(initial_state=self.scan_message, name='SignElectrumMessageFlow')

    async def scan_message(self):
        result = await ScanQRFlow(qr_types=[QRType.QR, QRType.UR2],
                                  ur_types=[ur.Value.PSBT],
                                  data_description='a message').run()

        if result is None:
            self.set_result(None)
            return

        if isinstance(result, ur.Value):
            # Sparrow sends a BIP-322 request as a PSBT. Copy it, since the decoder reuses its storage.
            self.psbt = bytes(result.unwrap_psbt())
            self.goto(self.validate_bip322_request)
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

    async def validate_bip322_request(self):
        (values, error) = await spinner_task('Validating Message',
                                             validate_bip322_request_task,
                                             args=[self.psbt])
        self.psbt = None

        if error:
            await ErrorPage(error).show()
            self.set_result(False)
            return

        (self.message, self.subpath, self.bip322_request) = values

        self.goto(self.show_message)

    async def show_message(self):
        self.addr_format = get_addr_type_from_deriv(self.subpath)

        if self.addr_format is None:
            self.addr_format = AF_CLASSIC

        with stash.SensitiveValues() as sv:
            node = sv.derive_path(self.subpath)
            self.address = sv.chain.address(node, self.addr_format)

        display_address = stylize_address(self.address)

        result = await LongTextPage(centered=True,
                                    text='\n' + escape_text(self.message),
                                    footer=message_review_warning(self.message),
                                    require_scroll_to_end=True,
                                    card_header={'title': 'Message'}).show()

        if not result:
            self.set_result(False)
            return

        result = await LongQuestionPage(text='Sign message with this address?\n\n{}'.format(display_address),
                                        right_micron=microns.Sign,
                                        margins=MARGIN_FOR_ADDRESSES,
                                        top_margin=8).show()

        if not result:
            self.set_result(False)
            return

        self.goto(self.do_sign)

    async def do_sign(self):
        (sig, address, error) = await spinner_task('Signing message', sign_text_file_task,
                                                   args=[self.message, self.subpath, self.addr_format, self.address,
                                                         self.bip322_request])
        if error is None:
            self.signature = sig
            self.goto(self.show_signed)
        else:
            await ErrorPage(text='Error while signing message: {}'.format(error)).show()
            self.set_result(False)
            return

    async def show_signed(self):
        qr_type = QRType.QR
        qr_data = self.signature
        if self.bip322_request is not None:
            # Send the request back signed, as a PSBT like the one the wallet sent.
            qr_type = QRType.UR2
            qr_data = ur.new_psbt(self.signature)

        result = await ShowQRPage(qr_type=qr_type,
                                  qr_data=qr_data,
                                  right_micron=microns.Checkmark).show()

        self.set_result(result)
