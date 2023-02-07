# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# apply_passphrase_flow.py - Ask user to enter a passphrase, then apply it.

from flows import Flow
from pages import SuccessPage, TextInputPage, ErrorPage, QuestionPage
from tasks import apply_passphrase_task
from utils import spinner_task
from errors import Error
from translations import t, T
from constants import MAX_PASSPHRASE_LENGTH


class ApplyPassphraseFlow(Flow):
    def __init__(self, passphrase=None):

        # Caller wants to set this passphrase
        if passphrase is not None:
            self.passphrase = passphrase
            super().__init__(initial_state=self.apply_passphrase, name='ApplyPassphraseFlow')
        else:
            self.passphrase = ''
            super().__init__(initial_state=self.enter_passphrase, name='ApplyPassphraseFlow')

    async def enter_passphrase(self):
        self.passphrase = await TextInputPage(card_header={'title': 'Enter Passphrase'},
                                              initial_text=self.passphrase,
                                              max_length=MAX_PASSPHRASE_LENGTH).show()
        if self.passphrase is not None:
            self.goto(self.apply_passphrase)
        else:
            self.set_result(False)

    async def apply_passphrase(self):
        if len(self.passphrase) == 0:
            result = await QuestionPage(text='Clear the active passphrase?').show()
            if result:
                msg = 'Clearing passphrase'
            else:
                self.set_result(False)
                return
        else:
            msg = 'Applying passphrase'

        (error,) = await spinner_task(msg, apply_passphrase_task, args=[self.passphrase])
        if error is None:
            import common
            from utils import start_task, xfp2str

            # Make a success page
            if len(self.passphrase) == 0:
                await SuccessPage(
                    text='Passphrase cleared\n\nFingerprint:\n\n{}'.format(
                        xfp2str(common.settings.get('xfp', '---')))
                ).show()
            else:
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
        elif error is Error.NOT_BIP39_MODE:
            await ErrorPage(text='Unable to apply passphrase. Not in BIP39 mode.').show()

        self.set_result(error is None)
