# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# view_backup_code_flow.py - Confirm the user wants to see this sensitive info, then show it.

from flows import Flow


class ViewBackupCodeFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.confirm_show, name='ViewBackupCodeFlow')

    async def confirm_show(self):
        from pages.question_page import QuestionPage

        result = await QuestionPage(
            'The next screen will show your backup code.\n\n' +
            'Display this sensitive information?').show()

        if result:
            self.goto(self.show_backup_code)
        else:
            self.set_result(False)

    async def show_backup_code(self):
        from utils import spinner_task
        from tasks import get_backup_code_task
        from pages.error_page import ErrorPage
        from pages.backup_code_page import BackupCodePage

        (backup_code, error) = await spinner_task('Retrieving\nBackup Code', get_backup_code_task)
        if error is None:
            await BackupCodePage(digits=backup_code, editable=False, card_header={'title': 'Backup Code'}).show()
            self.set_result(True)
        else:
            await ErrorPage(text='Unable to retrieve Backup Code: {}'.format(error)).show()
            self.set_result(False)
