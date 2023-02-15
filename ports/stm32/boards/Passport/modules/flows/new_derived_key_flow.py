# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# new_derived_key_flow.py - Create a new derived key

from flows import Flow


class NewDerivedKeyFlow(Flow):
    def __init__(self):
        self.index = None
        self.num_words = None
        self.next_index = None
        self.key_name = None
        self.key_type = None
        super().__init__(initial_state=self.select_type, name="NewDerivedKeyFlow")

    async def select_type(self):
        from pages import ChooserPage
        import microns
        from derived_key import key_types
        from wallets.utils import get_next_derived_key_index

        options = []
        for key_type in key_types:
            options.append({'label': key_type, 'value': key_type})

        selection = await ChooserPage(card_header={'title': 'Key Type'}, options=options).show()

        if selection is None:
            self.set_result(None)
            return

        self.key_type = selection
        self.next_index = get_next_derived_key_index(self.key_type)
        self.goto(self.enter_index)

    async def enter_index(self):
        from pages import TextInputPage, ErrorPage
        import microns
        from utils import get_derived_key_by_index
        result = await TextInputPage(card_header={'title': 'Key Number'}, numeric_only=True,
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
        existing_key = get_derived_key_by_index(self.index, self.key_type)
        if existing_key is not None:
            if len(existing_key['name']) == 0:
                error_message = 'A previously deleted {} key used key number {}.' \
                                .format(self.key_type, self.index)
            else:
                error_message = 'A {} key named "{}" already exists with key number {}.' \
                                .format(self.key_type, existing_key['name'], self.index)
            await ErrorPage(error_message).show()
            return
        self.goto(self.enter_key_name)

    async def enter_key_name(self):
        from constants import MAX_ACCOUNT_NAME_LEN
        from pages import TextInputPage, ErrorPage
        import microns
        from utils import get_derived_key_by_name
        result = await TextInputPage(card_header={'title': 'Key Name'},
                                     initial_text='' if self.key_name is None else self.key_name,
                                     max_length=MAX_ACCOUNT_NAME_LEN,
                                     left_micron=microns.Back,
                                     right_micron=microns.Checkmark).show()
        if result is not None:
            if len(result) == 0:
                # Just show the page again
                return
            self.key_name = result

            # Check for existing account with this name
            existing_key = get_derived_key_by_name(self.key_name, self.key_type)
            if existing_key is not None:
                await ErrorPage('{} key ##{} already exists with the name "{}".'
                                .format(self.key_type,
                                        existing_key['index'],
                                        self.key_name)).show()
                return

            self.goto(self.save_key)
        else:
            self.back()

    async def save_key(self):
        from pages import SuccessPage, ErrorPage
        from tasks import save_new_derived_key_task
        from utils import spinner_task
        (error,) = await spinner_task('Saving New Key Details', save_new_derived_key_task,
                                      args=[self.index, self.key_name, self.key_type])
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
        self.goto(self.generate_key)

    async def generate_key(self):
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
