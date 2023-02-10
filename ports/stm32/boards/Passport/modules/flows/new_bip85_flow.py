# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# new_bip85_flow.py - Create a new BIP85 seed

from flows import Flow


class NewBIP85Flow(Flow):
    def __init__(self):
        from wallets.utils import get_next_bip85_index
        self.index = None
        self.num_words = None
        self.next_index = get_next_bip85_index()
        self.seed_name = None
        super().__init__(initial_state=self.enter_index, name="ExportBIP85QRFlow")

    async def enter_index(self):
        from pages import TextInputPage, ErrorPage
        import microns
        from utils import get_bip85_entry_by_index
        result = await TextInputPage(card_header={'title': 'Seed Number'}, numeric_only=True,
                                     initial_text='' if self.next_index is None else str(self.next_index),
                                     max_length=10,
                                     left_micron=microns.Back,
                                     right_micron=microns.Checkmark).show()
        if result is None:
            self.set_result(False)
            return
        if len(result) == 0:
            return  # Try again
        self.index = int(result)
        existing_entry = get_bip85_entry_by_index(self.index)
        if existing_entry is not None:
            await ErrorPage('A seed named "{}" already exists with seed number {}.'
                            .format(existing_entry['name'], self.index)).show()
            return
        self.goto(self.enter_seed_name)

    async def enter_seed_name(self):
        from constants import MAX_ACCOUNT_NAME_LEN
        from pages import TextInputPage, ErrorPage
        import microns
        from utils import get_bip85_entry_by_name
        result = await TextInputPage(card_header={'title': 'Seed Name'},
                                     initial_text='' if self.seed_name is None else self.seed_name,
                                     max_length=MAX_ACCOUNT_NAME_LEN,
                                     left_micron=microns.Back,
                                     right_micron=microns.Checkmark).show()
        if result is not None:
            if len(result) == 0:
                # Just show the page again
                return
            self.seed_name = result

            # Check for existing account with this name
            existing_entry = get_bip85_entry_by_name(self.seed_name)
            if existing_entry is not None:
                await ErrorPage(text='Seed #{} already exists with the name "{}".'.format(
                    existing_entry['index'], self.seed_name)).show()
                return

            self.goto(self.save_entry)
        else:
            self.back()

    async def save_entry(self):
        from pages import SuccessPage, ErrorPage
        from tasks import save_new_bip85_entry_task
        from utils import spinner_task
        (error,) = await spinner_task('Saving New Seed Details', save_new_bip85_entry_task,
                                      args=[self.index, self.seed_name])
        if error is None:
            from flows import AutoBackupFlow

            await SuccessPage(text='New Seed Details Saved').show()
            await AutoBackupFlow().run()
            self.set_result(True)
        else:
            await ErrorPage(text='New Seed Details not saved: {}'.format(error)).show()
            self.set_result(False)

    async def choose_num_words(self):
        from pages import ChooserPage
        options = [{'label': '24 words', 'value': 24},
                   {'label': '12 words', 'value': 12}]
        self.num_words = await ChooserPage(card_header={'title': 'Number of Words'}, options=options).show()
        if self.num_words is None:
            self.set_result(False)
            return
        self.goto(self.generate_seed)

    async def generate_seed(self):
        from utils import spinner_task
        from tasks import bip85_seed_task
        from pages import ErrorPage
        (self.seed, error) = await spinner_task(text='Generating Seed',
                                                     task=bip85_seed_task,
                                                     args=[self.num_words, self.index])
        if self.error is None:
            self.goto(self.show_seed_words)
        else:
            await ErrorPage(error).show()
            self.set_result(False)

    async def show_seed_words(self):
        from flows import ViewSeedWordsFlow
        await ViewSeedWordsFlow(bip85_seed=self.seed, bip85_index=self.index).run()
        self.goto(self.show_qr_code)

    async def show_qr_code(self):
        from pages import ShowQRPage
        from utils import B2A
        import microns
        await ShowQRPage(qr_data=B2A(self.seed), right_micron=microns.Checkmark).show()
        self.set_result(True)
