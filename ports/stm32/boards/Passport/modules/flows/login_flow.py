# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# login_flow.py - Login to Passport

import lvgl as lv
from flows import Flow
from pages import PINEntryPage, ShutdownPage, ErrorPage
from tasks import login_task
from utils import spinner_task
import microns

BRICK_WARNING_NUM_ATTEMPTS = const(5)


class LoginFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.enter_pin, name='LoginFlow')

    async def enter_pin(self):
        try:
            self.pin = await PINEntryPage(
                card_header={'title': 'Enter PIN'},
                security_words_message='Recognize these Security Words?',
                left_micron=microns.Shutdown,
                right_micron=microns.Checkmark).show()
            if self.pin is not None:
                self.goto(self.check_pin)
            else:
                await ShutdownPage().show()
        except BaseException:
            pass

    async def check_pin(self):
        (result, _error) = await spinner_task('Validating PIN', login_task, args=[self.pin])
        if result:
            self.set_result(True)
        else:
            # print('goto error!!!!')
            self.goto(self.show_error)

    async def show_error(self):
        from common import pa

        # Switch to bricked view if no more attempts
        if pa.attempts_left == 0:
            self.goto(self.show_bricked_message)
            return

        if pa.attempts_left == 1:
            attempt_msg = 'This is your FINAL attempt'
        else:
            attempt_msg = 'You have {} attempts left'.format(pa.attempts_left)

        if pa.attempts_left <= BRICK_WARNING_NUM_ATTEMPTS:
            brick_warning = ' before Passport is permanently disabled'
        else:
            brick_warning = ''

        msg = 'Wrong PIN!\n\n{}{}.'.format(attempt_msg, brick_warning)
        result = await ErrorPage(text=msg,
                                 left_micron=microns.Shutdown,
                                 right_micron=microns.Retry).show()
        if result:
            self.pin = None
            self.goto(self.enter_pin)
        else:
            await ShutdownPage().show()

    async def show_bricked_message(self):
        from common import pa

        msg = '''This Passport is now permanently disabled.

Restore a microSD backup or seed phrase onto a new Passport to recover your funds.''' % pa.num_fails

        result = await ErrorPage(text=msg,
                                 left_micron=microns.Shutdown,
                                 right_micron=microns.Retry).show()
        if result:
            import machine
            machine.reset()
        else:
            await ShutdownPage().show()
