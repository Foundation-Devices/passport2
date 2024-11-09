# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# change_pin_flow.py - Change the user's PIN

from flows import Flow
from pages import PINEntryPage, ErrorPage, SuccessPage
from tasks import change_pin_task
from utils import spinner_task
from translations import t, T
import microns
from common import settings
from serializations import sha256


class ChangePINFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.enter_old_pin, name='ChangePINFlow')

    async def enter_old_pin(self):
        (self.old_pin, is_done) = await PINEntryPage(
            card_header={'title': 'Enter Current PIN'},
            security_words_message='Recognize these Security Words?',

            left_micron=microns.Back,
            right_micron=microns.Forward).show()
        if not is_done:
            self.set_result(None)
            return
        else:
            self.goto(self.enter_new_pin)

    async def enter_new_pin(self):
        (self.new_pin, is_done) = await PINEntryPage(
            card_header={'title': 'Enter New PIN'},
            security_words_message='Remember these Security Words',

            left_micron=microns.Back,
            right_micron=microns.Forward).show()
        if not is_done:
            self.back()
        else:
            self.goto(self.confirm_new_pin)

    async def confirm_new_pin(self):
        (confirmed_pin, is_done) = await PINEntryPage(
            card_header={'title': 'Confirm New PIN'},
            security_words_message='Remember these Security Words',
            left_micron=microns.Back,
            right_micron=microns.Forward).show()
        if not is_done:
            self.back()
        else:
            if self.new_pin == confirmed_pin:
                self.goto(self.change_pin)
            else:
                self.goto(self.new_pin_mismatch)

    async def change_pin(self):
        (result, error) = await spinner_task('Changing PIN', change_pin_task,
                                             args=[self.old_pin, self.new_pin])
        if result:
            settings.set_volatile('pin_prefix_hash', sha256(self.new_pin[:4]))
            self.goto(self.show_success)
        else:
            self.goto(self.show_error)

    async def new_pin_mismatch(self):
        await ErrorPage(text='Unable to change PIN.\n\nThe new PINs don\'t match.').show()
        self.reset(self.enter_old_pin)

    async def show_error(self):
        if await ErrorPage(text='Unable to change PIN.\n\nThe current PIN is incorrect.').show():
            self.reset(self.enter_old_pin)
        else:
            self.set_result(False)

    async def show_success(self):
        await SuccessPage(text='PIN changed successfully!\n\nIt will take effect after rebooting.').show()
        self.set_result(True)
