# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# restore_backup_flow.py -Restore a selected backup file to Passport.

import lvgl as lv
from constants import TOTAL_BACKUP_CODE_DIGITS, NUM_BACKUP_PASSWORD_WORDS
from flows import Flow, FilePickerFlow, ErasePassportFlow
import microns
from pages import (
    BackupCodePage,
    ErrorPage,
    InsertMicroSDPage,
    PredictiveTextInputPage,
    QuestionPage,
    RecoveryModeChooserPage,
    SuccessPage,
    YesNoChooserPage
)
from utils import get_backups_folder_path, spinner_task, get_backup_code_as_password
from tasks import restore_backup_task, get_backup_code_task
from errors import Error
import common


class RestoreBackupFlow(Flow):
    def __init__(self, refresh_cards_when_done=False, autobackup=True, full_backup=False):
        super().__init__(initial_state=self.check_if_erased, name='RestoreBackupFlow')
        self.refresh_cards_when_done = refresh_cards_when_done
        self.backup_code = [None] * TOTAL_BACKUP_CODE_DIGITS
        self.backup_password_words = []
        self.backup_password_prefixes = []
        self.full_backup = full_backup
        self.autobackup = autobackup

    async def check_if_erased(self):
        from common import pa
        if not pa.is_secret_blank():
            result = await YesNoChooserPage(
                icon=lv.LARGE_ICON_QUESTION,
                text='You must erase Passport before you can restore.',
                yes_text='Erase Now',
                no_text='Back',
                initial_value=False).show()
            if result:
                # If user proceeds all the way through, Passport will be erased and then restarted,
                # so if we get back here, they did NOT erase.
                await ErasePassportFlow().run()

            self.set_result(False)
        else:
            self.goto(self.choose_file)

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
            self.goto(self.select_recovery_mode)

    async def select_recovery_mode(self):
        from pages.recovery_mode_chooser_page import RecoveryMode

        result = await RecoveryModeChooserPage().show()
        if result is None:
            self.back()
        else:
            if result == RecoveryMode.BACKUP_CODE_20_DIGITS:
                self.goto(self.enter_backup_code)
            else:
                self.goto(self.enter_backup_password)

    async def enter_backup_password(self):
        result = await PredictiveTextInputPage(
            word_list='bytewords',
            total_words=NUM_BACKUP_PASSWORD_WORDS,
            initial_words=self.backup_password_words).show()
        if result is None:
            cancel = await QuestionPage(text='Cancel password entry? ' +
                                        'All progress will be lost.').show()
            if cancel:
                self.back()
        else:
            self.backup_password_words, self.backup_password_prefixes = result
            self.decryption_password = (' ').join(self.backup_password_words)
            # print('6 words: decryption_password={}'.format(self.decryption_password))
            self.goto(self.do_restore)

    async def enter_backup_code(self):
        result = await BackupCodePage(digits=self.backup_code, card_header={'title': 'Enter Backup Code'}).show()
        if result is not None:
            self.backup_code = result
            self.decryption_password = get_backup_code_as_password(self.backup_code)
            # print('20-digits: decryption_password={}'.format(self.decryption_password))
            self.goto(self.do_restore)
        else:
            self.back()

    async def do_restore(self):
        from utils import start_task
        from flows import AutoBackupFlow, BackupFlow
        from pages import InfoPage

        # TODO: Change from spinner to ProgressPage and pass on_progress instead of None below.
        (error,) = await spinner_task(
            'Restoring Backup',
            restore_backup_task,
            args=[self.decryption_password,
                  self.backup_file_path])
        (new_backup_code, error_2) = await spinner_task('Restoring Backup', get_backup_code_task)

        if error is None:
            await SuccessPage(text='Restore Complete!').show()
            self.set_result(True)

            if self.full_backup:
                if error_2 is not None or self.backup_code != new_backup_code:
                    await InfoPage("You will receive a new Backup Code to use with your new Passport.").show()
                    await BackupFlow().run()
            elif self.autobackup:
                await AutoBackupFlow(offer=True).run()

            if self.refresh_cards_when_done:
                common.ui.update_cards(is_init=True)

                async def start_main_task():
                    common.ui.start_card_task(card_idx=common.ui.active_card_idx)

                start_task(start_main_task())

                await self.wait_to_die()
            else:
                self.set_result(True)

        elif error is Error.MICROSD_CARD_MISSING:
            result = await InsertMicroSDPage().show()
            if not result:
                self.set_result(False)
        elif error is Error.INVALID_BACKUP_CODE:
            result = await ErrorPage(
                'Invalid Backup Code.',
                left_micron=microns.Back,
                right_micron=microns.Retry).show()
            if result:
                # Retry
                self.back()
            else:
                # Exit
                self.set_result(False)
        elif error is Error.FILE_READ_ERROR:
            await ErrorPage(text='Unable to read backup file.').show()
            self.set_result(False)
        elif error is Error.INVALID_BACKUP_FILE_HEADER:
            await ErrorPage(text='Unable to read backup file header. The backup may have been modified.').show()
            self.set_result(False)
        elif error is Error.CORRUPT_BACKUP_FILE:
            await ErrorPage(text='Corrupt data in backup file. The backup may have been modified.').show()
            self.set_result(False)
