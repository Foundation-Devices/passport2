# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# scv_flow.py - Supply Chain Validation Flow

import lvgl as lv
from flows import Flow, ScanQRFlow
from pages import ShowQRPage, QuestionPage, ChooserPage
from styles.colors import HIGHLIGHT_TEXT_HEX
from data_codecs.qr_type import QRType
from utils import a2b_hex, recolor
from ubinascii import hexlify as b2a_hex
from pincodes import PinAttempt
from foundation import ur
import microns
import foundation
import passport
import common


class ScvFlow(Flow):
    def __init__(self, envoy=True, ask_to_skip=True):
        """
        :param envoy: True for Envoy App flow. False is manual Supply Chain Validation.
        """

        super().__init__(initial_state=self.show_intro,
                         name='ScvFlow',
                         statusbar={'title': 'SECURITY CHECK', 'icon': 'ICON_SHIELD'})
        self.words = None
        self.envoy = envoy
        self.ask_to_skip = ask_to_skip
        self.uuid = None

    async def show_intro(self):
        from pages import ShieldPage
        from flows import SeriesOfPagesFlow

        if self.envoy:
            messages = [{'text': 'On the next screen, scan the QR code shown in Envoy.'}]
        else:
            messages = [{'text': 'Let\'s confirm Passport was not tampered with during shipping.'},
                        {'text': 'Next, scan the Security Check '
                         'QR code from https://validate.foundation.xyz.'}]

        result = await SeriesOfPagesFlow(ShieldPage, messages).run()

        if result:
            self.goto(self.scan_qr_challenge)
        else:
            self.set_result(False)

    async def scan_qr_challenge(self):
        qr_types = [QRType.UR2] if self.envoy else None
        ur_types = [ur.Value.PASSPORT_REQUEST] if self.envoy else None
        result = await ScanQRFlow(qr_types=qr_types,
                                  ur_types=ur_types,
                                  data_description='a supply chain validation challenge').run()
        if result is None:
            self.goto(self.prompt_skip)
            return

        if self.envoy:
            passport_request = result.unwrap_passport_request()

            self.uuid = passport_request.uuid()
            scv_id = passport_request.scv_challenge_id()
            scv_signature = passport_request.scv_challenge_signature()
        else:
            parts = result.split(' ')
            if len(parts) != 2:
                await self.show_error('Security Check QR code is invalid.\n'
                                      'There\'s not enough information in the QR code.')
                return

            try:
                scv_id = a2b_hex(parts[0])
                scv_signature = a2b_hex(parts[1])
            except ValueError:
                await self.show_error('Security Check QR code is invalid.\n')
                return

        id_hash = bytearray(32)
        foundation.sha256(b2a_hex(scv_id), id_hash)

        signature_valid = passport.verify_supply_chain_server_signature(id_hash, scv_signature)
        if not signature_valid:
            await self.show_error('Security Check signature is invalid.')
            return

        self.words = PinAttempt.supply_chain_validation_words(scv_id)
        if self.envoy:
            self.goto(self.show_envoy_scan_msg)
        else:
            self.goto(self.show_manual_response)

    async def show_envoy_scan_msg(self):
        from pages import InfoPage

        result = await InfoPage(
            text='On Envoy, select {next}, and scan the following QR code.'
            .format(next=recolor(HIGHLIGHT_TEXT_HEX, 'Next')),
            left_micron=microns.Back,
            right_micron=microns.Forward).show()
        if not result:
            self.back()
        else:
            self.goto(self.show_envoy_response)

    async def show_envoy_response(self):
        from common import system

        (version, _, _, _, _) = system.get_software_info()
        crypto_response = ur.new_passport_response(uuid=self.uuid,
                                                   word1=self.words[0],
                                                   word2=self.words[1],
                                                   word3=self.words[2],
                                                   word4=self.words[3],
                                                   model=ur.PASSPORT_MODEL_BATCH2,
                                                   version=version)

        result = await ShowQRPage(qr_type=QRType.UR2,
                                  qr_data=crypto_response,
                                  caption='Scan with Envoy',
                                  left_micron=microns.Back,
                                  right_micron=microns.Forward).show()
        if not result:
            self.back()
        else:
            self.goto(self.ask_if_valid)

    async def show_manual_response(self):
        from pages import ShieldPage

        lines = ['{}. {}\n'.format(idx + 1, word) for idx, word in enumerate(self.words)]
        words = ''.join(lines)

        result = await ShieldPage(text=words,
                                  left_micron=microns.Retry).show()
        if not result:
            self.back()
        else:
            self.goto(self.ask_if_valid)

    async def ask_if_valid(self):
        from pages import ErrorPage

        options = [{'label': 'Passed', 'value': True}, {'label': 'Failed', 'value': False}]
        result = await ChooserPage(
            text='Security Check Result',
            options=options,
            icon=lv.LARGE_ICON_SHIELD,
            initial_value=options[0].get('value'),
            left_micron=microns.Back,
            right_micron=microns.Checkmark).show()
        if result is None:
            self.back()
        elif result is True:
            common.settings.set('validated_ok', True)
            self.set_result(True)
        else:
            result = await ErrorPage(text='''This Passport may have been tampered with.

Please contact support@
foundationdevices.com.''', left_micron=microns.Cancel, right_micron=microns.Retry).show()
            if result:
                self.goto(self.scan_qr_challenge)
            else:
                self.goto(self.prompt_skip)

    async def prompt_skip(self):

        if not self.ask_to_skip:
            common.settings.set('validated_ok', True)
            self.set_result(True)
            return

        skip = await QuestionPage(
            text='Skip Security Check?\n\n{}'.format(
                recolor(HIGHLIGHT_TEXT_HEX, '(Not recommended)'))
        ).show()
        if skip:
            common.settings.set('validated_ok', True)
            self.set_result(True)
        else:
            self.back()

    async def show_error(self, message):
        from pages import ErrorPage

        await ErrorPage(text=message).show()
        self.reset(self.show_intro)
