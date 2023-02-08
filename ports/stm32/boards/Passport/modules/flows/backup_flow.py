# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# backup_flow.py - Backup Passport to microSD

import lvgl as lv
from flows import Flow
from constants import TOTAL_BACKUP_CODE_DIGITS
from errors import Error
import microns
from pages.question_page import QuestionPage
from styles.colors import HIGHLIGHT_TEXT_HEX


class BackupFlow(Flow):
    def __init__(self):
        from common import settings
        super().__init__(initial_state=self.show_intro, name='BackupFlow')
        self.backup_quiz_passed = settings.get('backup_quiz', False)
        self.quiz_result = [None] * TOTAL_BACKUP_CODE_DIGITS

        self.statusbar = {'title': 'BACKUP', 'icon': lv.ICON_BACKUP}

    async def show_intro(self):
        from pages import InfoPage
        from utils import recolor
        import stash

        if self.backup_quiz_passed:
            msgs = ['Passport is about to create an updated microSD backup.',
                    'The Backup Code is the same as what you were previously shown.']
        else:
            msgs = ['Passport is about to create your first encrypted microSD backup.',
                    'The next screen will show you the Backup Code that is {} to decrypt the backup.'.format(
                        recolor(HIGHLIGHT_TEXT_HEX, 'REQUIRED')),
                    'We recommend writing down the Backup Code on the included security card.',
                    'We consider this safe since physical access to the microSD card is required to access the backup.']
        if stash.bip39_passphrase != '':
            msgs.append('The current passphrase applied to Passport will not be saved as part of this backup.')

        result = await InfoPage(
            icon=lv.LARGE_ICON_BACKUP,
            text=msgs,
            left_micron=microns.Back,
            right_micron=microns.Forward).show()
        if result:
            self.goto(self.get_backup_code)
        else:
            result = await QuestionPage(text='Skip initial Backup?\n\n{}'.format(
                recolor(HIGHLIGHT_TEXT_HEX, '(Not recommended)')), left_micron=microns.Retry).show()
            if result:
                self.set_result(False)
            else:
                return

    async def get_backup_code(self):
        from utils import spinner_task
        from tasks import get_backup_code_task
        from pages import ErrorPage

        (self.backup_code, error) = await spinner_task('Retrieving Backup Code', get_backup_code_task)
        if error is None:
            if self.backup_quiz_passed:
                self.goto(self.do_backup, save_curr=False)
            else:
                self.goto(self.show_backup_code, save_curr=False)
        else:
            await ErrorPage(text='Unable to retrieve Backup Code: {}'.format(error)).show()
            self.set_result(False)

    async def show_backup_code(self):
        from pages import InfoPage, BackupCodePage

        result = await BackupCodePage(
            digits=self.backup_code,
            editable=False,
            card_header={'title': 'Backup Code'}).show()
        if result:
            result = await InfoPage(
                icon=lv.LARGE_ICON_BACKUP,
                card_header={'title': 'Backup Code Quiz'},
                text='Let\'s check that you recorded the Backup Code correctly.').show()
            if not result:
                self.back()
            else:
                self.goto(self.do_backup_code_quiz)
        else:
            self.back()

    async def do_backup_code_quiz(self):
        from pages import BackupCodePage, SuccessPage, ErrorPage

        result = await BackupCodePage(digits=self.quiz_result, card_header={'title': 'Enter Backup Code'}).show()
        if result is not None:
            if result == self.backup_code:
                from common import settings
                settings.set('backup_quiz', True)
                await SuccessPage(text='You entered the Backup Code correctly!').show()
                self.goto(self.do_backup)
            else:
                # Save this so the user doesn't lose their input
                self.quiz_result = result
                await ErrorPage(text='The Backup Code you entered is incorrect, please try again.').show()
        else:
            # Clear out quiz result
            self.quiz_result = [None] * TOTAL_BACKUP_CODE_DIGITS
            self.back()

    async def do_backup(self):
        from utils import spinner_task
        from tasks import save_backup_task
        from pages import InsertMicroSDPage, SuccessPage, ErrorPage

        # TODO: Change from spinner to ProgressPage and pass on_progress instead of None below.
        (error,) = await spinner_task('Writing Backup', save_backup_task, args=[None, self.backup_code])
        if error is None:
            await SuccessPage(text='Backup Complete!').show()
            self.set_result(True)
        elif error is Error.MICROSD_CARD_MISSING:
            result = await InsertMicroSDPage().show()
            if not result:
                self.set_result(False)
        elif error is Error.FILE_WRITE_ERROR:
            await ErrorPage(text='Unable to write to backup file.').show()
            self.set_result(False)
