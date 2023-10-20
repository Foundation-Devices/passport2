# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# set_initial_pin_flow.py - Change the user's PIN

import lvgl as lv
from flows import Flow
import microns


class SetInitialPINFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.intro, name='SetInitialPINFlow')

        self.statusbar = {'title': 'SET PIN', 'icon': 'ICON_PIN'}

    async def intro(self):
        from common import pa
        from pages import InfoPage

        if not pa.is_blank():
            # Just let the parent flow continue on
            self.set_result(True)
            return

        result = await InfoPage(
            icon=lv.LARGE_ICON_PIN,
            text=['Now it\'s time to set your 6-12 digit PIN.',
                  'There is no way to recover a lost PIN or reset Passport.',
                  'Please record your PIN somewhere safe.'],
            left_micron=microns.Back,
            right_micron=microns.Forward).show()
        if result:
            self.goto(self.enter_new_pin)
        else:
            self.set_result(False)

    async def enter_new_pin(self):
        from pages import PINEntryPage
        (self.new_pin, is_done) = await PINEntryPage(
            card_header={'title': 'Enter PIN'},
            security_words_message='Remember these Security Words',
            left_micron=microns.Back,
            right_micron=microns.Forward).show()
        if not is_done:
            self.back()
        else:
            self.goto(self.confirm_new_pin)

    async def confirm_new_pin(self):
        from pages import PINEntryPage
        from tasks import set_initial_pin_task, login_task
        from utils import spinner_task
        from common import settings
        from serializations import sha256

        (confirmed_pin, is_done) = await PINEntryPage(
            card_header={'title': 'Confirm PIN'},
            security_words_message='Remember these Security Words',
            left_micron=microns.Back,
            right_micron=microns.Forward).show()
        if not is_done:
            self.back()
        else:
            if self.new_pin == confirmed_pin:
                settings.set_volatile('pin_prefix_hash', sha256(self.new_pin[:4]))

                (result, error) = await spinner_task('Setting initial PIN', set_initial_pin_task,
                                                     args=[self.new_pin])
                if not result:
                    self.goto(self.show_error)

                (result, error) = await spinner_task('Logging in', login_task, args=[self.new_pin])
                if result:
                    self.goto(self.show_success)
                else:
                    # print('goto error!!!!')
                    self.goto(self.show_error)
            else:
                self.goto(self.new_pin_mismatch)

    async def new_pin_mismatch(self):
        from pages import ErrorPage

        await ErrorPage(text='Unable to set initial PIN.\n\nThe PINs don\'t match.', right_micron=microns.Retry).show()
        self.reset(self.enter_new_pin)

    async def show_success(self):
        from pages import SuccessPage

        await SuccessPage(text='PIN set successfully!').show()
        self.set_result(True)

    async def show_error(self):
        from pages import ErrorPage

        # print('set_initial_pin_flow: error')
        await ErrorPage(text='Unable to set initial PIN!', right_micron=microns.Retry).show()
        self.set_result(False)
