# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# restore_seed_flow.py -Restore a seed to Passport by entering the seed words.


from flows import Flow
import microns
from pages import ErrorPage, PredictiveTextInputPage, SeedLengthChooserPage, SuccessPage, QuestionPage
from utils import spinner_task
from tasks import save_seed_task


class RestoreSeedFlow(Flow):
    def __init__(self, refresh_cards_when_done=False):
        super().__init__(initial_state=self.choose_seed_len, name='RestoreSeedFlow')
        self.refresh_cards_when_done = refresh_cards_when_done
        self.seed_words = []

    async def choose_seed_len(self):
        self.seed_length = await SeedLengthChooserPage().show()
        if self.seed_length is None:
            self.set_result(False)
        else:
            self.goto(self.explain_input_method)

    async def explain_input_method(self):
        from pages import InfoPage

        result = await InfoPage([
            "Passport uses predictive text input to help you restore your seed words.",
            "Example: If you want to enter \"car\", type 2 2 7 and select \"car\" from the dropdown."]
        ).show()
        self.goto(self.enter_seed_words)

    async def enter_seed_words(self):
        result = await PredictiveTextInputPage(
            word_list='bip39',
            total_words=self.seed_length,
            initial_words=self.seed_words).show()
        if result is None:
            cancel = await QuestionPage(
                text='Cancel seed entry? All progress will be lost.').show()
            if cancel:
                self.set_result(False)
                return
        else:
            self.seed_words, self.prefixes = result
            self.goto(self.validate_seed_words)

    async def validate_seed_words(self):
        from trezorcrypto import bip39

        # self.mnemonic = ' '.join(self.seed_words)
        self.mnemonic = 'brick repeat nothing grunt genius trap hollow meat hawk jacket denial miss impose gorilla best logic divorce good broken prison illness awkward banana electric'

        if not bip39.check(self.mnemonic):
            self.goto(self.invalid_seed)
        else:
            self.goto(self.valid_seed)

    async def invalid_seed(self):
        result = await ErrorPage(text='Seed phrase is invalid. One or more of your seed words is incorrect.',
                                 left_micron=microns.Cancel, right_micron=microns.Retry).show()
        if result is None:
            cancel = await QuestionPage(
                text='Cancel seed entry? All progress will be lost.').show()
            if cancel:
                self.set_result(False)
                return

        # Retry
        self.goto(self.enter_seed_words)

    async def valid_seed(self):
        from foundation import bip39

        entropy = bytearray(33)  # Includes and extra byte for the checksum bits

        len = bip39.mnemonic_to_bits(self.mnemonic, entropy)

        if len == 264:  # 24 words x 11 bits each
            trim_pos = 32
        elif len == 198:  # 18 words x 11 bits each
            trim_pos = 24
        elif len == 132:  # 12 words x 11 bits each
            trim_pos = 16
        entropy = entropy[:trim_pos]  # Trim off the excess (including checksum bits)

        (error,) = await spinner_task('Saving seed', save_seed_task, args=[entropy])
        if error is None:
            import common
            await SuccessPage(text='New seed restored and saved.').show()

            if self.refresh_cards_when_done:
                common.ui.full_cards_refresh()

                await self.wait_to_die()
            else:
                self.set_result(True)
        else:
            # WIP: This is not complete - offer backup?
            pass
