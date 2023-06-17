# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# erase_passport_flow.py - Confirm the user wants to erase Passport, then erase Passport's wallet
#                          and reset wallet-related settings.

import lvgl as lv
from flows import Flow
from pages import SuccessPage, QuestionPage, LongQuestionPage
from tasks import erase_passport_task
from utils import spinner_task
from translations import t, T
import microns
import passport


class ErasePassportFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.confirm_erase, name='ErasePassportFlow')

    def on_reset(self, _t):
        self.reset_timer._del()
        self.reset_timer = None
        self.success_page.set_result(True)

    async def confirm_erase(self):
        if not await QuestionPage(
                'Are you sure you want to erase this Passport? All funds will be lost if not backed up.').show():
            self.set_result(False)
            return

        page_class = QuestionPage if passport.IS_COLOR else LongQuestionPage
        if not await page_class(
            'Without a proper backup, you could lose all funds associated with this device.\n\n' +
                'Please confirm you understand these risks.').show():
            self.set_result(False)
            return

        self.goto(self.do_erase)

    async def do_erase(self):
        import machine
        from pages import ShutdownPage, ErrorPage

        from common import system
        (error,) = await spinner_task('Erasing Passport', erase_passport_task, args=[False])
        if error is None:
            # Make a success page
            self.success_page = SuccessPage(text='Erase Complete.\n\nRestarting...')

            # Set a timer that will close it in a second
            # TODO: Page has an auto_close_timeout that could be passed through StatusPage, SuccessPage, ErrorPage, etc.
            self.reset_timer = lv.timer_create(self.on_reset, 2000, None)

            # Show the page -- if user happens to press a key ahead of this, we
            await self.success_page.show()

            if self.reset_timer is not None:
                self.reset_timer._del()
                self.reset_timer = None

            machine.reset()

        else:
            # This should neer happen now, since erase_passport_task only returns None
            result = await ErrorPage(
                text='Erasing Passport has failed: {}'.format(error),
                left_micron=microns.Shutdown,
                right_micron=microns.Retry).show()
            if result:
                pass
            else:
                await ShutdownPage().show()
