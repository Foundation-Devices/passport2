# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# new_derived_key_flow.py - Create a new derived key

from flows import Flow


class NewDerivedKeyFlow(Flow):
    def __init__(self, context=None):
        from wallets.utils import get_next_derived_key_index
        from common import settings

        self.index = None
        self.num_words = None
        self.key_name = None
        self.key_type = context
        self.xfp = settings.get('xfp')
        self.next_index = get_next_derived_key_index(self.key_type['tn'], self.xfp)
        super().__init__(initial_state=self.key_limit_warning, name="NewDerivedKeyFlow")

    async def key_limit_warning(self):
        from utils import get_derived_keys
        from constants import MAX_DERIVED_KEYS
        from pages import ErrorPage, InfoPage
        import microns

        keys = get_derived_keys()
        xfp_keys = [key for key in keys if key['xfp'] == self.xfp]

        if len(xfp_keys) == 0:
            text = 'There is space for {} keys per wallet, \
and keys can not be deleted. Create keys wisely.'.format(MAX_DERIVED_KEYS)
            result = await InfoPage(text, left_micron=microns.Back).show()

            if not result:
                self.set_result(False)
                return

        if len(xfp_keys) >= MAX_DERIVED_KEYS:
            text = 'You\'ve reached the limit of {} keys in this wallet.'.format(MAX_DERIVED_KEYS)
            await ErrorPage(text).show()
            self.set_result(False)
            return

        self.goto(self.passphrase_warning)

    async def passphrase_warning(self):
        from pages import LongTextPage
        import microns
        import stash

        if len(stash.bip39_passphrase) > 0:
            text = '''\
\n\nThis new key will be linked to your active passphrase. \
It will only be displayed when this same passphrase is applied. Continue?'''
            result = await LongTextPage(text=text,
                                        left_micron=microns.Cancel,
                                        right_micron=microns.Checkmark,
                                        centered=True).show()
            if not result:
                self.set_result(False)
                return

        self.goto(self.enter_index)

    async def enter_index(self):
        from pages import TextInputPage, ErrorPage, QuestionPage
        import microns
        from utils import get_derived_key_by_index
        from flows import RenameDerivedKeyFlow

        if not self.key_type['indexed']:
            self.index = 0
        else:
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
        existing_key = get_derived_key_by_index(self.index, self.key_type['tn'], self.xfp)
        if existing_key is not None:
            if not self.key_type['indexed']:
                error_message = 'You already have a {} named "{}".' \
                                .format(self.key_type['title'], existing_key['name'])
                await ErrorPage(error_message).show()
                self.set_result(False)
                return
            else:
                error_message = 'A {} named "{}" already exists with key number {}.' \
                                .format(self.key_type['title'], existing_key['name'], self.index)
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
            existing_key = get_derived_key_by_name(self.key_name, self.key_type['tn'], self.xfp)
            if existing_key is not None:
                await ErrorPage('{} ##{} already exists with the name "{}".'
                                .format(self.key_type['title'],
                                        existing_key['index'],
                                        self.key_name)).show()
                return

            self.goto(self.save_key)
        else:
            if not self.key_type['indexed']:
                self.set_result(False)
            else:
                self.back()

    async def save_key(self):
        from pages import SuccessPage, ErrorPage
        from tasks import save_new_derived_key_task
        from utils import spinner_task
        from common import keypad
        import lvgl as lv
        (error,) = await spinner_task('Saving New Key Details', save_new_derived_key_task,
                                      args=[self.index,
                                            self.key_name,
                                            self.key_type['tn'],
                                            self.xfp])
        if error is None:
            from flows import AutoBackupFlow

            await SuccessPage(text='New Seed Details Saved').show()
            await AutoBackupFlow().run()
            self.set_result(True)
        else:
            await ErrorPage(text='New Seed Details not saved: {}'.format(error)).show()
            self.set_result(False)
