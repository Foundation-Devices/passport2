# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# restore_seed_flow.py -Restore a seed to Passport by entering the seed words.


from flows import Flow, RandomFinalWordFlow
import microns
from pages import ErrorPage, PredictiveTextInputPage, SuccessPage, QuestionPage
from utils import spinner_task, insufficient_randomness
from tasks import save_seed_task
from public_constants import SEED_LENGTHS
import lvgl as lv


class RestoreSeedFlow(Flow):
    def __init__(self, refresh_cards_when_done=False, autobackup=True, full_backup=False,
                 temporary=False):
        self.refresh_cards_when_done = refresh_cards_when_done
        self.seed_format = None
        self.seed_length = None
        self.validate_text = None
        self.index = 0
        self.seed_words = []
        self.full_backup = full_backup
        self.autobackup = autobackup
        self.statusbar = {'title': 'IMPORT SEED', 'icon': 'ICON_SEED'}
        self.temporary = temporary

        initial_state = self.choose_temporary
        if self.temporary:
            initial_state = self.explain_temporary

        super().__init__(initial_state=initial_state, name='RestoreSeedFlow')

    async def choose_temporary(self):
        from pages import ChooserPage

        text = 'Would you like to make a permanent seed, or a temporary seed?'
        options = [{'label': 'Permanent', 'value': True},
                   {'label': 'Temporary', 'value': False}]

        permanent = await ChooserPage(text=text,
                                      card_header={'title': 'Seed Type'},
                                      options=options).show()
        if permanent is None:
            self.set_result(False)
            return

        if permanent:
            self.goto(self.choose_restore_method)
        else:
            self.goto(self.explain_temporary)

    async def explain_temporary(self):
        from pages import InfoPage
        import microns

        result = await InfoPage(
            icon=lv.LARGE_ICON_SEED,
            text='This temporary seed will not be saved, so be sure you have a backup, or create one during setup',
            left_micron=microns.Back,
            right_micron=microns.Forward).show()

        if not result:
            if not self.back():
                self.set_result(None)
            return

        self.goto(self.choose_restore_method)

    async def choose_restore_method(self):
        from pages import ChooserPage
        from data_codecs.qr_type import QRType

        options = [{'label': '12 Words', 'value': 12},
                   {'label': '24 Words', 'value': 24},
                   {'label': 'Compact SeedQR', 'value': QRType.COMPACT_SEED_QR},
                   {'label': 'SeedQR', 'value': QRType.SEED_QR}]

        choice = await ChooserPage(card_header={'title': 'Seed Format'}, options=options).show()

        if choice is None:
            if not self.back():
                self.set_result(False)
            return

        self.seed_format = choice
        if self.seed_format in SEED_LENGTHS:
            self.seed_length = choice
            self.validate_text = 'Seed phrase'
            self.goto(self.explain_input_method)
        else:
            if self.seed_format == QRType.SEED_QR:
                self.validate_text = 'SeedQR'
            else:
                self.validate_text = 'Compact SeedQR'
            self.goto(self.scan_qr)

    async def scan_qr(self):
        from flows import ScanQRFlow
        from pages import InfoPage, SeedWordsListPage
        import microns
        from data_codecs.qr_type import QRType

        result = await ScanQRFlow(explicit_type=self.seed_format,
                                  data_description=self.validate_text).run()

        if result is None:
            self.back()
            return

        self.seed_words = result

        plural_label = 's' if len(result) == 24 else ''
        result = await InfoPage('Confirm the seed words in the following page{}.'.format(plural_label)).show()

        if not result:
            self.back()
            return

        result = await SeedWordsListPage(words=self.seed_words, left_micron=microns.Cancel).show()

        if not result:
            self.back()
            return

        self.goto(self.validate_seed_words)

    async def explain_input_method(self):
        from pages import InfoPage
        import microns

        result = await InfoPage([
            "Passport uses predictive text input to help you import your seed words.",
            "Example: If you want to enter \"car\", type 2 2 7 and select \"car\" from the dropdown."],
            left_micron=microns.Back,
        ).show()

        if not result:
            self.back()
            return

        self.goto(self.enter_seed_words)

    async def enter_seed_words(self):
        result = await PredictiveTextInputPage(
            word_list='bip39',
            total_words=self.seed_length,
            initial_words=self.seed_words,
            start_index=self.index).show()

        if result is None:
            cancel = await QuestionPage(
                text='Cancel seed entry? All progress will be lost.').show()

            if cancel:
                self.set_result(False)
                return

            self.index = 0
            return

        self.seed_words, self.prefixes, get_last_word = result

        if get_last_word:

            last_word = await RandomFinalWordFlow(self.seed_words).run()

            if not last_word:
                self.index = self.seed_length - 1
                return  # Go back to input a last word

            self.seed_words.append(last_word)

        if insufficient_randomness(self.seed_words):
            text = "This seed contains 3 or more repeat words and may put funds at risk.\n\nSave seed and continue?"
            result2 = await ErrorPage(text=text,
                                      left_micron=microns.Cancel).show()

            if not result2:
                self.index = 0
                return  # Restart seed input

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
        from flows import AutoBackupFlow, BackupFlow
        from utils import get_seed_from_words

        entropy = get_seed_from_words(self.mnemonic)
        text = '{} seed'.format('Applying' if self.temporary else 'Saving')
        (error,) = await spinner_task(text, save_seed_task, args=[entropy])
        if error is None:
            import common

            text = 'New seed imported and {}'.format('applied' if self.temporary else 'saved')
            await SuccessPage(text=text).show()
            if self.full_backup:
                await BackupFlow(initial_backup=True).run()
            elif self.autobackup:
                await AutoBackupFlow(offer=True).run()

            if self.refresh_cards_when_done:
                common.ui.full_cards_refresh()

                await self.wait_to_die()
            else:
                self.set_result(True)
        else:
            text = 'Unable to {} seed'.format('apply' if self.temporary else 'save')
            await ErrorPage(text).show()
            self.set_result(False)
