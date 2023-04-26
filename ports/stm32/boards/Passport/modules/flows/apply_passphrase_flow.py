# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# apply_passphrase_flow.py - Ask user to enter a passphrase, then apply it.

from flows import Flow


class ApplyPassphraseFlow(Flow):
    def __init__(self, passphrase=None):
        import stash

        # Caller wants to set this passphrase
        self.attempted = False
        self.prev_passphrase = stash.bip39_passphrase
        self.passphrase = passphrase
        self.msg = 'Apply'
        if self.passphrase is not None:
            if len(self.passphrase) == 0:
                super().__init__(initial_state=self.clear_passphrase, name='ApplyPassphraseFlow')
            else:
                super().__init__(initial_state=self.apply_passphrase, name='ApplyPassphraseFlow')
        else:
            super().__init__(initial_state=self.explainer, name='ApplyPassphraseFlow')

    def check_attempt(self):
        if self.attempted:
            self.passphrase = self.prev_passphrase
            self.msg = 'Clear' if len(self.passphrase) == 0 else 'Revert'
            self.goto(self.apply_passphrase)
        else:
            self.set_result(False)

    async def explainer(self):
        from pages import InfoPage
        import microns

        result = await InfoPage(text='All passphrases are valid, and passphrases are forgotten upon shutdown.',
                                left_micron=microns.Back).show()

        if not result:
            self.set_result(False)
            return

        self.goto(self.enter_passphrase)

    async def enter_passphrase(self):
        from pages import TextInputPage
        from constants import MAX_PASSPHRASE_LENGTH

        passphrase = await TextInputPage(card_header={'title': 'Enter Passphrase'},
                                         initial_text=self.passphrase or '',
                                         max_length=MAX_PASSPHRASE_LENGTH).show()

        # Exit text input, means we want to go back, and no need to prompt for reverting to no passphrase
        if passphrase is None or (len(passphrase) == 0 and passphrase == self.prev_passphrase):
            self.check_attempt()
            return

        # Clear passphrase, previous passphrase is in use
        if len(passphrase) == 0:
            self.goto(self.clear_passphrase)
            return

        # Revert passphrase to entered field, no need to check xfp
        if passphrase == self.prev_passphrase:
            self.check_attempt()
            return

        self.msg = 'Apply'
        self.passphrase = passphrase
        self.goto(self.apply_passphrase)

    async def clear_passphrase(self):
        from pages import QuestionPage
        result = await QuestionPage(text='Clear the active passphrase?').show()

        if not result:
            self.back()
            return

        self.msg = 'Clear'
        self.passphrase = ''
        self.goto(self.apply_passphrase)

    async def apply_passphrase(self):
        from utils import spinner_task
        from errors import Error
        from tasks import apply_passphrase_task
        from pages import ErrorPage

        (error,) = await spinner_task("{}ing passphrase".format(self.msg),
                                      apply_passphrase_task,
                                      args=[self.passphrase])

        if error is not None:
            if error is Error.NOT_BIP39_MODE:
                await ErrorPage(text='Unable to {} passphrase. Not in BIP39 mode.'.format(self.msg.lower())).show()
            else:
                await ErrorPage(text='Unable to {} passphrase.'.format(self.msg.lower())).show()
            self.set_result(False)
            return

        self.goto(self.confirm_xfp)

    async def confirm_xfp(self):
        import common
        from utils import start_task, xfp2str
        from pages import QuestionPage, SuccessPage

        # Make a success page
        if len(self.passphrase) == 0 or self.passphrase == self.prev_passphrase:
            await SuccessPage(
                text='Passphrase {}ed\n\nFingerprint:\n\n{}'.format(
                    self.msg.lower(),  # this is either 'revert' or 'clear' at this point
                    xfp2str(common.settings.get('xfp', '---')))
            ).show()
        else:
            self.attempted = True
            result = await QuestionPage(
                text='Passphrase applied\n\nFingerprint correct?\n\n{}'.format(
                    xfp2str(common.settings.get('xfp', '---')))
            ).show()

            if result is False:
                self.goto(self.enter_passphrase)
                return

        common.ui.update_cards(stay_on_same_card=True)

        async def start_main_task():
            common.ui.start_card_task(card_idx=common.ui.active_card_idx)

        start_task(start_main_task())

        await self.wait_to_die()

        self.set_result(True)
