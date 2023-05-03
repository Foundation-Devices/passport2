# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# scv_flow.py - Supply Chain Validation Flow

import lvgl as lv
from flows import Flow
from pages import ScanQRPage, ShowQRPage, QRScanResult
from pages.chooser_page import ChooserPage
from styles.colors import HIGHLIGHT_TEXT_HEX
from data_codecs.qr_type import QRType
from utils import a2b_hex
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

        super().__init__(initial_state=self.show_intro, name='ScvFlow')
        self.words = None
        self.envoy = envoy
        self.ask_to_skip = ask_to_skip
        self.uuid = None

        self.statusbar = {'title': 'SECURITY CHECK', 'icon': lv.ICON_SHIELD}

    async def show_intro(self):
        from pages import ShieldPage

        text = []
        # Only show the first item for manual flow
        if not self.envoy:
            text.append('Let\'s confirm Passport was not tampered with during shipping.')

        if self.envoy:
            text.append('On the next screen, scan the QR code shown in Envoy.')
        else:
            text.append('On the next screen, scan the Security Check QR code from validate.foundationdevices.com.')

        result = await ShieldPage(
            text=text,
            left_micron=microns.Back, right_micron=microns.Forward).show()
        if result:
            self.goto(self.scan_qr_challenge)
        else:
            self.set_result(False)

    async def scan_qr_challenge(self):
        from utils import recolor
        result = await ScanQRPage(left_micron=microns.Cancel, right_micron=None).show()

        # User did not scan anything
        if result is None:
            from pages import QuestionPage
            if self.envoy:
                cancel = await QuestionPage(
                    text='Cancel Envoy Setup?\n\n{}'.format(
                        recolor(HIGHLIGHT_TEXT_HEX, '(Not recommended)'))
                ).show()
                if cancel:
                    self.set_result(None)
                else:
                    return
            else:
                if not self.ask_to_skip:
                    self.set_result(True)
                else:
                    skip = await QuestionPage(
                        text='Skip Security Check?\n\n{}'.format(
                            recolor(HIGHLIGHT_TEXT_HEX, '(Not recommended)'))
                    ).show()
                    if skip:
                        common.settings.set('validated_ok', True)
                        self.set_result(True)
                    else:
                        self.back()
            return

        # Scan succeeded -- verify its content
        if self.envoy:
            if not is_valid_envoy_qrcode(result):
                await self.show_error(("Security Check QR code is invalid.\n"
                                       "Make sure you're scanning an Envoy QR code."))
                return
        else:
            if not is_valid_website_qrcode(result):
                await self.show_error(("Security Check QR code is invalid.\n"
                                       "There was an error scanning the QR code."))
                return

        if self.envoy:
            passport_request = result.data.unwrap_passport_request()

            self.uuid = passport_request.uuid()
            challenge = {
                'id': passport_request.scv_challenge_id(),
                'signature': passport_request.scv_challenge_signature(),
            }
        else:
            try:
                parts = result.data.split(' ')
                if len(parts) != 2:
                    await self.show_error(("Security Check QR code is invalid.\n"
                                           "There's not enough information in the QR code."))
                    return

                challenge = {
                    'id': parts[0],
                    'signature': parts[1],
                }
                # print('Manual: challenge={}'.format(challenge))
            except Exception as e:
                await self.show_error(("Security Check QR code is invalid.\n"
                                       "Make sure you're scanning a manual setup QR code."))
                return

        id_hash = bytearray(32)
        id_bin = a2b_hex(challenge['id']) if isinstance(challenge['id'], str) else challenge['id']
        id_hex = challenge['id'] if isinstance(challenge['id'], str) else b2a_hex(challenge['id'])
        foundation.sha256(id_hex,
                          id_hash)
        if isinstance(challenge['signature'], str):
            signature = a2b_hex(challenge['signature'])
        else:
            signature = challenge['signature']

        signature_valid = passport.verify_supply_chain_server_signature(id_hash, signature)
        if not signature_valid:
            await self.show_error('Security Check signature is invalid.')
            return

        self.words = PinAttempt.supply_chain_validation_words(id_bin)

        if self.envoy:
            self.goto(self.show_envoy_scan_msg)
        else:
            self.goto(self.show_manual_response)

    async def show_envoy_scan_msg(self):
        from pages import InfoPage
        from utils import recolor

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

        words = ''
        for idx, word in enumerate(self.words):
            words += '               {}. {}\n'.format(idx + 1, word)
        words = words[:-1]

        result = await ShieldPage(text=words, card_header={'title': 'Security Check'}, centered=False,
                                  left_micron=microns.Retry, right_micron=microns.Forward).show()
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
                self.goto(self.ask_to_skip)

    async def ask_to_skip(self):
        from pages import QuestionPage
        from utils import recolor

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
        from pages import InfoPage

        await InfoPage(text=message).show()
        self.reset(self.show_intro)


def is_valid_envoy_qrcode(result):
    if not isinstance(result, QRScanResult):
        return False

    if (
            (result.error is not None) or
            (result.data is None) or
            (not isinstance(result.data, ur.Value))
    ):
        return False

    return True


def is_valid_website_qrcode(result):
    if not isinstance(result, QRScanResult):
        return False

    if (
            (result.error is not None) or
            (result.data is None)
    ):
        return False

    return True
