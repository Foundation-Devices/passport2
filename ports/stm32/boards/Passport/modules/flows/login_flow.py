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
import common


class LoginFlow(Flow):
    def __init__(self, auto_pin=None):
        if auto_pin is not None:
            self.pin = auto_pin
            super().__init__(initial_state=self.check_pin, name='LoginFlow')
        else:
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
        (result, _error) = await spinner_task('Validating PIN', login_task, args=[self.pin], no_anim=True)
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

        result = await ErrorPage(text='Wrong PIN!\n\nYou have {} attempts remaining.'.format(pa.attempts_left),
                                 left_micron=microns.Shutdown,
                                 right_micron=microns.Retry).show()
        if result:
            self.pin = None
            self.goto(self.enter_pin)
        else:
            await ShutdownPage().show()

    async def show_bricked_message(self):
        from common import pa

        msg = '''After %d failed PIN attempts, this Passport is now permanently disabled.

Restore a microSD backup or seed phrase onto a new Passport to recover your funds.''' % pa.num_fails

        result = await ErrorPage(text='Fatal Error.\n\n{}'.format(msg),
                                 left_micron=microns.Shutdown,
                                 right_micron=microns.Retry).show()
        if result:
            import machine
            machine.reset()
        else:
            await ShutdownPage().show()
