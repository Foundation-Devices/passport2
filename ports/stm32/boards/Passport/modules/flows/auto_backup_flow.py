# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# auto_backup_flow.py - Check to see if microSD is inserted and, if so, backup automatically

from flows import Flow

MSG_CLOSE_TIMEOUT = 1000


class AutoBackupFlow(Flow):
    def __init__(self, reason='System information changed.', offer=False):
        super().__init__(initial_state=self.check_for_microsd, name='AutoBackupFlow')
        self.reason = reason
        self.offer = offer

    async def check_for_microsd(self):
        from files import CardSlot, CardMissingError
        from pages import QuestionPage

        try:
            with CardSlot() as card:
                # If the card is inserted, we can try to run the backup flow
                self.goto(self.get_backup_code)
        except CardMissingError:
            if self.offer:
                result = await QuestionPage(text='{}\n\nBackup to microSD now?'.format(self.reason)).show()
                if result:
                    self.goto(self.get_backup_code)
                else:
                    self.set_result(False)
            else:
                self.set_result(False)  # No backup was done

    async def get_backup_code(self):
        from tasks import get_backup_code_task
        from utils import spinner_task

        (self.backup_code, error) = await spinner_task(
            'AutoBackup Running\nDon\'t remove microSD!',
            get_backup_code_task)
        if error is None:
            self.goto(self.do_backup, save_curr=False)
        else:
            from pages import ErrorPage
            await ErrorPage(text='Unable to retrieve Backup Code: {}'.format(error)).show(
                auto_close_timeout=MSG_CLOSE_TIMEOUT)
            self.set_result(False)

    async def do_backup(self):
        from flows import BackupCommonFlow

        result = await BackupCommonFlow(self.backup_code, automatic=True).run()
        self.set_result(result)
