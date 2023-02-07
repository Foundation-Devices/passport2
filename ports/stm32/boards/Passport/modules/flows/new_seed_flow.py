# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# new_seed_flow.py - Create a new random seed

from flows import Flow
from pages import ErrorPage, QuestionPage, SuccessPage
from tasks import new_seed_task, save_seed_task
from utils import has_secrets, spinner_task
from translations import t, T


class NewSeedFlow(Flow):
    def __init__(self, refresh_cards_when_done=False, autobackup=True, show_words=False, full_backup=False):
        super().__init__(initial_state=self.confirm_generate, name='NewSeedFlow')
        self.refresh_cards_when_done = refresh_cards_when_done
        self.autobackup = autobackup
        self.show_words = show_words
        self.full_backup = full_backup

    async def confirm_generate(self):
        # Ensure we don't overwrite an existing seed
        if has_secrets():
            await ErrorPage(text='Passport already has a seed!').show()
            self.set_result(False)
            return

        result = await QuestionPage(text='Generate a new seed phrase now?').show()
        if result:
            self.goto(self.generate_seed)
        else:
            self.set_result(False)

    async def generate_seed(self):
        (seed, error) = await spinner_task('Generating Seed', new_seed_task)
        if error is None:
            self.seed = seed
            self.goto(self.save_seed)
        else:
            self.error = error
            self.goto(self.show_error)

    async def save_seed(self):
        (error,) = await spinner_task('Saving Seed', save_seed_task, args=[self.seed])
        if error is None:
            if self.show_words:
                self.goto(self.show_seed_words)
            else:
                self.goto(self.show_success)
        else:
            self.error = 'Unable to save seed.'
            self.goto(self.show_error)

    async def show_seed_words(self):
        from flows import ViewSeedWordsFlow
        await ViewSeedWordsFlow().run()
        self.goto(self.show_success)

    async def show_success(self):
        import common
        from flows import AutoBackupFlow, BackupFlow

        await SuccessPage(text='New seed created and saved.').show()
        if self.full_backup:
            await BackupFlow().run()
        elif self.autobackup:
            await AutoBackupFlow(offer=True).run()

        if self.refresh_cards_when_done:
            common.ui.full_cards_refresh()

            await self.wait_to_die()
        else:
            self.set_result(True)

    async def show_error(self):
        await ErrorPage(self.error).show()
        self.set_result(False)
