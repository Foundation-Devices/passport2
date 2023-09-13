# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# rename_account_flow.py - Rename an account

from constants import MAX_ACCOUNT_NAME_LEN
from flows import Flow
import microns
from pages import ErrorPage, SuccessPage, TextInputPage, ErrorPage
from tasks import rename_account_task
from utils import get_account_by_name, spinner_task
from translations import t, T


class RenameAccountFlow(Flow):
    def __init__(self):
        from common import ui

        self.account = ui.get_active_account()
        self.error = None
        self.new_account_name = None

        if self.account is not None:
            initial_state = self.ask_for_name
        else:
            self.error = 'No active account!'
            initial_state = self.show_error

        super().__init__(initial_state=initial_state, name='RenameAccountFLow')

    async def ask_for_name(self):
        from common import settings

        name = self.account.get('name') if self.new_account_name is None else self.new_account_name
        result = await TextInputPage(initial_text=name,
                                     max_length=MAX_ACCOUNT_NAME_LEN,
                                     left_micron=microns.Cancel,
                                     right_micron=microns.Checkmark).show()
        if result is not None:
            self.new_account_name = result

            # Check for existing account with this name
            existing_account = get_account_by_name(self.new_account_name, settings.get('xfp'))
            if existing_account is not None:
                await ErrorPage(text='Account #{} already exists with the name "{}".'.format(
                    existing_account.get('acct_num'), self.new_account_name)).show()
                return

            self.goto(self.do_rename)
        else:
            self.set_result(False)

    async def do_rename(self):
        from common import ui, settings

        (error,) = await spinner_task('Renaming account', rename_account_task,
                                      args=[self.account.get('acct_num'),
                                            self.new_account_name,
                                            settings.get('xfp')])
        if error is None:
            import common
            from utils import start_task
            from flows import AutoBackupFlow

            ui.set_card_header(title=self.new_account_name)
            await SuccessPage(text='Account renamed').show()

            await AutoBackupFlow().run()

            common.ui.update_cards(stay_on_same_card=True)

            async def start_main_task():
                common.ui.start_card_task(card_idx=common.ui.active_card_idx)

            start_task(start_main_task())

            await self.wait_to_die()

        else:
            await ErrorPage(text='Account NOT renamed: {}'.format(self.error)).show()
            self.set_result(False)

    async def show_error(self):
        await ErrorPage(self.error).show()
        self.set_result(False)
