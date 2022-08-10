# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# new_account_flow.py - Create a new random seed

from constants import MAX_ACCOUNT_NAME_LEN, MAX_ACCOUNTS
from flows import Flow
import microns
from pages import ErrorPage, SuccessPage, TextInputPage, ErrorPage
from tasks import save_new_account_task
from utils import get_account_by_name, get_account_by_number, get_accounts, spinner_task
from translations import t, T
from wallets.utils import get_next_account_num


class NewAccountFlow(Flow):
    def __init__(self):
        initial_state = self.enter_account_num
        self.accounts = get_accounts()
        if len(self.accounts) >= MAX_ACCOUNTS:
            initial_state = self.show_account_limit_message

        super().__init__(initial_state=initial_state, name='NewAccountFlow')
        self.error = None

        # Suggest the next available account number to the user
        self.account_num = get_next_account_num()
        self.account_name = None

    def on_save_account_done(self, error=None):
        self.error = error
        self.spinner_page.set_result(error is None)

    async def show_account_limit_message(self):
        await ErrorPage(text='You\'ve reached the limit of {} accounts.'.format(MAX_ACCOUNTS)).show()
        self.set_result(False)

    async def enter_account_num(self):

        result = await TextInputPage(card_header={'title': 'Account Number'}, numeric_only=True,
                                     initial_text='' if self.account_num is None else str(self.account_num),
                                     max_length=10,
                                     left_micron=microns.Back,
                                     right_micron=microns.Checkmark).show()
        if result is not None:
            if len(result) == 0:
                return  # Try again

            self.account_num = int(result)

            # Check for existing account with this number
            existing_account = get_account_by_number(self.account_num)
            if existing_account is not None:
                await ErrorPage(text='An account named "{}" already exists with account number {}.'.format(
                    existing_account.get('name'), self.account_num)).show()
                return

            self.goto(self.enter_account_name)
        else:
            self.set_result(False)

    async def enter_account_name(self):
        result = await TextInputPage(card_header={'title': 'Account Name'},
                                     initial_text='' if self.account_name is None else self.account_name,
                                     max_length=MAX_ACCOUNT_NAME_LEN,
                                     left_micron=microns.Back,
                                     right_micron=microns.Checkmark).show()
        if result is not None:
            if len(result) == 0:
                # Just show the page again
                return
            self.account_name = result

            # Check for existing account with this name
            existing_account = get_account_by_name(self.account_name)
            if existing_account is not None:
                await ErrorPage(text='Account #{} already exists with the name "{}".'.format(
                    existing_account.get('acct_num'), self.account_name)).show()
                return

            self.goto(self.save_account)
        else:
            self.back()

    async def save_account(self):
        from common import ui
        (error,) = await spinner_task('Saving New Account', save_new_account_task,
                                      args=[self.account_num, self.account_name])
        if error is None:
            from flows import AutoBackupFlow

            ui.update_cards(is_new_account=True)
            await SuccessPage(text='New Account Saved').show()
            await AutoBackupFlow().run()
            self.set_result(True)
        else:
            await ErrorPage(text='New Account not saved: {}'.format(self.error)).show()
            self.set_result(False)

    async def show_error(self):
        await ErrorPage(self.error).show()
        self.set_result(False)
