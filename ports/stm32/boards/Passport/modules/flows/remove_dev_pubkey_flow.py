# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# remove_dev_pubkey_flow.py - Flow to remove the currently installed dev pubkey (after confirming removal)

from flows.flow import Flow


class RemoveDevPubkeyFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.check_for_user_signed_firmware)

    async def check_for_user_signed_firmware(self):
        from common import system
        from pages.error_page import ErrorPage

        if system.is_user_firmware_installed():
            result = await ErrorPage(
                'You must install official Foundation firmware before you can remove the Developer PubKey.').show()
            self.set_result(result)
            return

        self.goto(self.remove_dev_pubkey)

    async def remove_dev_pubkey(self):
        from common import system
        from pages.succes_page import SuccessPage
        from pages.error_page import ErrorPage
        from pages.question_page import QuestionPage
        from utils import clear_cached_pubkey

        zero_pubkey = bytearray(64)

        # Confirm the user knows the potential consequences
        result = await QuestionPage(text='Remove the Developer PubKey?').show()
        if not result:
            self.set_result(False)
            return

        # Remove it
        clear_cached_pubkey()
        result = system.set_user_firmware_pubkey(zero_pubkey)
        if result:
            await SuccessPage(text='Successfully Removed Developer PubKey.').show()
            self.set_result(True)
        else:
            await ErrorPage(text='Unable to Remove Developer PubKey.').show()
            self.set_result(False)
