# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# delete_account_flow.py - Delete the current account

import lvgl as lv
from flows import Flow
from pages import ErrorPage, SuccessPage, QuestionPage, ErrorPage
from tasks import delete_account_task
from utils import spinner_task
from translations import t, T


class DeleteAccountFlow(Flow):
    def __init__(self):
        from common import ui

        self.account = ui.get_active_account()
        self.error = None

        if self.account is not None:
            initial_state = self.check_account_zero
        else:
            self.error = 'No active account!'
            initial_state = self.show_error

        super().__init__(initial_state=initial_state, name='DeleteAccountFlow')

    async def check_account_zero(self):
        if self.account.get('acct_num') == 0:
            await ErrorPage(text='You can\'t delete account ##0.').show()
            self.set_result(False)
        else:
            self.goto(self.confirm_delete)

    async def confirm_delete(self):
        result = await QuestionPage(text='Delete this account?\n\n{}\n(##{})'.format(
            self.account.get('name'), self.account.get('acct_num'))).show()
        if result:
            self.goto(self.do_delete)
        else:
            self.set_result(False)

    async def do_delete(self):
        from common import settings

        (error,) = await spinner_task('Deleting Account', delete_account_task,
                                      args=[self.account.get('acct_num'),
                                            settings.get('xfp')])
        if error is None:
            import common
            from utils import start_task
            from flows import AutoBackupFlow

            await SuccessPage(text='Account Deleted').show()

            await AutoBackupFlow().run()

            common.ui.update_cards(is_delete_account=True)

            async def start_main_task():
                common.ui.start_card_task(card_idx=common.ui.active_card_idx)

            start_task(start_main_task())

            await self.wait_to_die()
        else:
            self.error = 'Account NOT deleted: {}'.format(error)
            self.goto(self.show_error)

    async def show_error(self):
        await ErrorPage(self.error).show()
        self.set_result(False)
