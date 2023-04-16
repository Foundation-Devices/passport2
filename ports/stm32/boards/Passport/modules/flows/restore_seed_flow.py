# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# restore_seed_flow.py -Restore a seed to Passport by entering the seed words.


from flows import Flow
import microns
from pages import ErrorPage, PredictiveTextInputPage, SuccessPage, QuestionPage
from utils import spinner_task
from tasks import save_seed_task


class RestoreSeedFlow(Flow):
    def __init__(self, refresh_cards_when_done=False):
        super().__init__(initial_state=self.choose_restore_method, name='RestoreSeedFlow')
        self.refresh_cards_when_done = refresh_cards_when_done
        self.seed_format = None
        self.seed_length = None
        self.validate_text = None
        self.seed_words = []

    async def choose_restore_method(self):
        from pages import ChooserPage
        from data_codecs.qr_type import QRType

        options = [{'label': '24 words', 'value': 24},
                   {'label': '12 words', 'value': 12},
                   {'label': 'Compact SeedQR', 'value': QRType.COMPACT_SEED_QR},
                   {'label': 'SeedQR', 'value': QRType.SEED_QR}]

        choice = await ChooserPage(card_header={'title': 'Seed Format'}, options=options).show()

        if choice is None:
            self.set_result(False)
            return

        self.seed_format = choice
        if self.seed_format in [12, 24]:
            self.seed_length = choice
            self.validate_text = 'Seed phrase'
            self.goto(self.explain_input_method)
        else:
            self.validate_text = 'SeedQR'
            self.goto(self.scan_qr)

    async def scan_qr(self):
        from flows import ScanQRFlow
        from pages import InfoPage, SeedWordsListPage
        import microns
        from data_codecs.qr_type import QRType

        compact_label = 'Compact ' if self.seed_format == QRType.COMPACT_SEED_QR else ''
        result = await ScanQRFlow(explicit_type=self.seed_format,
                                  data_description='{}SeedQR'
                                  .format(compact_label)).run()

        if result is None:
            self.back()
            return

        self.seed_words

        plural_label = 's' if len(result) == 24 else ''
        result = await InfoPage('Confirm the seed words in the following page{}.'.format(plural_label)).show()

        if not result:
            self.back()
            return

        # TODO: check that microns work right in this page
        result = await SeedWordsListPage(words=self.seed_words, left_micron=microns.Cancel).show()

        if not result:
            self.back()
            return

        self.goto(self.validate_seed_words)

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

        self.mnemonic = ' '.join(self.seed_words)

        if not bip39.check(self.mnemonic):
            self.goto(self.invalid_seed)
        else:
            self.goto(self.valid_seed)

    async def invalid_seed(self):
        result = await ErrorPage(text='{} is invalid. One or more of your seed words is incorrect.'
                                      .format(self.validate_text),
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

        entropy = bytearray(33)  # Includes an extra byte for the checksum bits

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
            await ErrorPage('Unable to save seed.').show()
