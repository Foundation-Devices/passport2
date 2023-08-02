# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# login_flow.py - Login to Passport

from flows.flow import Flow

_BRICK_WARNING_NUM_ATTEMPTS = const(5)


class LoginFlow(Flow):
    def __init__(self):
        self.pin = ''
        super().__init__(initial_state=self.enter_pin, name='LoginFlow')

    async def enter_pin(self):
        from pages.pin_entry_page import PINEntryPage
        from pages.shutdown_page import ShutdownPage
        import microns

        try:
            (self.pin, is_done) = await PINEntryPage(
                card_header={'title': 'Enter PIN'},
                security_words_message='Recognize these Security Words?',
                left_micron=microns.Shutdown,
                right_micron=microns.Checkmark,
                pin=self.pin).show()
            if is_done:
                self.goto(self.check_pin)
            else:
                await ShutdownPage().show()
        except BaseException:
            pass

    async def check_pin(self):
        from tasks import login_task
        from utils import spinner_task
        from serializations import sha256
        from common import settings

        (result, _error) = await spinner_task('Validating PIN', login_task, args=[self.pin])
        if result:
            settings.set_volatile('pin_prefix_hash', sha256(self.pin[:4]))
            self.set_result(True)
        else:
            # print('goto error!!!!')
            self.goto(self.show_error)

    async def show_error(self):
        from common import pa
        from pages.shutdown_page import ShutdownPage
        from pages.error_page import ErrorPage
        import microns

        # Switch to bricked view if no more attempts
        if pa.attempts_left == 0:
            self.goto(self.show_bricked_message)
            return

        if pa.attempts_left == 1:
            attempt_msg = 'This is your FINAL attempt'
        else:
            attempt_msg = 'You have {} attempts left'.format(pa.attempts_left)

        if pa.attempts_left <= _BRICK_WARNING_NUM_ATTEMPTS:
            brick_warning = ' before Passport is permanently disabled'
        else:
            brick_warning = ''

        msg = 'Wrong PIN!\n\n{}{}.'.format(attempt_msg, brick_warning)
        result = await ErrorPage(text=msg,
                                 left_micron=microns.Shutdown,
                                 right_micron=microns.Retry).show()
        if result:
            self.pin = ''
            self.goto(self.enter_pin)
        else:
            await ShutdownPage().show()

    async def show_bricked_message(self):
        from common import pa
        from pages.shutdown_page import ShutdownPage
        from pages.error_page import ErrorPage
        import microns

        msg = '''This Passport is now permanently disabled.

Restore a microSD backup or seed phrase onto a new Passport to recover your funds.'''

        result = await ErrorPage(text=msg,
                                 left_micron=microns.Shutdown,
                                 right_micron=microns.Retry).show()
        if result:
            import machine
            machine.reset()
        else:
            await ShutdownPage().show()
