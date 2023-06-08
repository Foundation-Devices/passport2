# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# verify_backup_flow.py - Verify a selected backup file.


from flows import Flow, FilePickerFlow
from pages import ErrorPage, SuccessPage, LongSuccessPage, InsertMicroSDPage
from utils import get_backups_folder_path, spinner_task
from tasks import verify_backup_task
from errors import Error
import passport


class VerifyBackupFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.choose_file, name='VerifyBackupFlow')

    async def choose_file(self):
        backups_path = get_backups_folder_path()
        result = await FilePickerFlow(initial_path=backups_path, suffix='.7z', show_folders=True).run()
        if result is None:
            # No file chosen, so go back to menu
            self.set_result(False)
            return

        _filename, full_path, is_folder = result
        if not is_folder:
            self.backup_file_path = full_path
            self.goto(self.do_verify)

    async def do_verify(self):
        (error,) = await spinner_task(
            'Verifying Backup',
            verify_backup_task,
            args=[self.backup_file_path])
        if error is None:
            page_class = SuccessPage if passport.IS_COLOR else LongSuccessPage
            await page_class(text='Backup file appears to be valid.\n\nPlease note this is only a check to ensure ' +
                             'the file has not been modified or damaged.').show()
            self.set_result(True)
        elif error is Error.MICROSD_CARD_MISSING:
            result = await InsertMicroSDPage().show()
            if not result:
                self.set_result(False)
        elif error is Error.FILE_READ_ERROR:
            await ErrorPage(text='Unable to verify CRC of backup file.  The backup may have been modified.').show()
            self.set_result(False)
        elif error is Error.INVALID_BACKUP_FILE_HEADER:
            await ErrorPage(text='Unable to read backup file header. The backup may have been modified.').show()
            self.set_result(False)
