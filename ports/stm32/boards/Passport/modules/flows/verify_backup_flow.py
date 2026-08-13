# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# verify_backup_flow.py - Verify a selected backup file.


from constants import TOTAL_BACKUP_CODE_DIGITS
from flows import FilePickerFlow, Flow
from pages import BackupCodePage, ErrorPage, InsertMicroSDPage, LongSuccessPage, SuccessPage
from utils import get_backup_code_as_password, get_backups_folder_path, spinner_task
from tasks import verify_backup_task
from errors import Error
import microns
import passport


class VerifyBackupFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.choose_file, name='VerifyBackupFlow')
        self.backup_code = [None] * TOTAL_BACKUP_CODE_DIGITS
        self.decryption_password = None

    async def choose_file(self):
        backups_path = get_backups_folder_path()
        result = await FilePickerFlow(initial_path=backups_path, suffix='.7z', show_folders=True).run()
        if result is None:
            # No file chosen, so go back to menu
            self.clear_backup_code()
            self.set_result(False)
            return

        _filename, full_path, is_folder = result
        if not is_folder:
            self.backup_file_path = full_path
            self.goto(self.enter_backup_code)

    async def enter_backup_code(self):
        result = await BackupCodePage(
            digits=self.backup_code,
            card_header={'title': 'Enter Backup Code'}).show()
        if result is None:
            self.back()
            return

        self.backup_code = result
        self.decryption_password = get_backup_code_as_password(self.backup_code)
        self.goto(self.do_verify)

    async def do_verify(self):
        (error,) = await spinner_task(
            'Verifying Backup',
            verify_backup_task,
            args=[self.decryption_password, self.backup_file_path])
        if error is None:
            self.clear_backup_code()
            page_class = SuccessPage if passport.IS_COLOR else LongSuccessPage
            await page_class(text='Backup decrypted successfully and passed its integrity check.').show()
            self.set_result(True)
        elif error is Error.MICROSD_CARD_MISSING:
            result = await InsertMicroSDPage().show()
            if not result:
                self.clear_backup_code()
                self.set_result(False)
        elif error is Error.INVALID_BACKUP_CODE:
            result = await ErrorPage(
                text='Unable to decrypt backup. The Backup Code may be incorrect, '
                     'or the backup may be damaged.',
                left_micron=microns.Back,
                right_micron=microns.Retry).show()
            self.decryption_password = None
            if result:
                self.back()
            else:
                self.clear_backup_code()
                self.set_result(False)
        elif error is Error.FILE_READ_ERROR:
            self.clear_backup_code()
            await ErrorPage(text='Unable to read backup file.').show()
            self.set_result(False)
        elif error is Error.INVALID_BACKUP_FILE_HEADER:
            self.clear_backup_code()
            await ErrorPage(text='Unable to read backup file header. The backup may have been modified.').show()
            self.set_result(False)
        elif error is Error.OUT_OF_MEMORY_ERROR:
            self.clear_backup_code()
            await ErrorPage(text='Not enough memory to verify this backup.').show()
            self.set_result(False)
        else:
            self.clear_backup_code()
            await ErrorPage(text='Unable to verify backup.').show()
            self.set_result(False)

    def clear_backup_code(self):
        self.backup_code = [None] * TOTAL_BACKUP_CODE_DIGITS
        self.decryption_password = None
