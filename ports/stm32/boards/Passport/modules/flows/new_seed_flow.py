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
    def __init__(self, refresh_cards_when_done=False, autobackup=True, full_backup=False):
        super().__init__(initial_state=self.check_for_seed, name='NewSeedFlow')
        self.refresh_cards_when_done = refresh_cards_when_done
        self.autobackup = autobackup
        self.full_backup = full_backup
        self.seed_length = None
        self.skip_seed_prompt = False

    async def check_for_seed(self):
        # Ensure we don't overwrite an existing seed
        if has_secrets():
            await ErrorPage(text='Passport already has a seed!').show()
            self.set_result(False)
            return

        self.goto(self.pick_length)

    async def pick_length(self):
        from public_constants import SEED_LENGTHS
        from pages import ChooserPage

        options = []
        for length in SEED_LENGTHS:
            options.append({'label': '{} Words'.format(length), 'value': length})

        self.seed_length = await ChooserPage(card_header={'title': 'Seed Length'}, options=options).show()
        if not self.seed_length:
            self.set_result(False)
        else:
            self.goto(self.confirm_generate)

    async def confirm_generate(self):
        result = await QuestionPage(text='Generate a new seed phrase now?').show()
        if result:
            self.goto(self.generate_seed)
        else:
            self.back()

    async def generate_seed(self):
        (seed, error) = await spinner_task('Generating Seed',
                                           new_seed_task,
                                           args=[self.seed_length])
        if error is None:
            self.seed = seed
            self.goto(self.save_seed)
        else:
            self.error = error
            self.goto(self.show_error)

    async def save_seed(self):
        (error,) = await spinner_task('Saving Seed', save_seed_task, args=[self.seed])
        if error is None:
            self.goto(self.do_backup)
        else:
            self.error = 'Unable to save seed.'
            self.goto(self.show_error)

    async def do_backup(self):
        from flows import AutoBackupFlow, BackupFlow

        backup_flow = None

        if self.full_backup:
            backup_flow = BackupFlow()
        elif self.autobackup:
            backup_flow = AutoBackupFlow(offer=True)

        if backup_flow is None:
            self.goto(self.show_seed_words)
            return

        # Run whichever backup flow is used, and
        # determine if the seed can be skipped
        self.skip_seed_prompt = await backup_flow.run()
        self.goto(self.show_seed_words)

    async def show_seed_words(self):
        from flows import ViewSeedWordsFlow
        await ViewSeedWordsFlow(initial=True,
                                allow_skip=self.skip_seed_prompt).run()
        self.goto(self.show_success)

    async def show_success(self):
        import common

        await SuccessPage(text='New seed created and saved.').show()

        if self.refresh_cards_when_done:
            common.ui.full_cards_refresh()

            await self.wait_to_die()
        else:
            self.set_result(True)

    async def show_error(self):
        await ErrorPage(self.error).show()
        self.set_result(False)
