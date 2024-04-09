# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# initial_seed_setup_flow.py - Menu to let user choose seed setup method

import lvgl as lv
from flows import Flow
from common import settings


class InitialSeedSetupFlow(Flow):
    def __init__(self, allow_backtrack=True, temporary=False, external_key=None):
        self.statusbar = {'title': 'CREATE SEED', 'icon': 'ICON_SEED'}
        self.allow_backtrack = allow_backtrack
        self.temporary = temporary
        self.external_key = external_key
        initial_state = self.show_intro
        if temporary:
            settings.enter_temporary_mode()
            # TODO: go to "explain_temporary" first
            if self.external_key:
                initial_state = self.apply_external_key
        super().__init__(initial_state=initial_state, name='InitialSeedSetupFlow')

    async def show_intro(self):
        from pages import InfoPage
        from utils import has_seed
        import microns

        # Pass silently if seed already exists
        if has_seed() and not self.temporary:
            self.set_result(True)
            return

        if self.allow_backtrack:
            left_micron = microns.Back
        else:
            left_micron = None

        result = await InfoPage(
            icon=lv.LARGE_ICON_SEED,
            text='Next, let\'s create or import a wallet seed.',
            left_micron=left_micron, right_micron=microns.Forward).show()
        if result:
            self.goto(self.show_seed_setup_menu)
        else:
            if self.temporary:
                settings.exit_temporary_mode()
            self.set_result(None)

    async def show_seed_setup_menu(self):
        from pages import ChooserPage
        from flows import NewSeedFlow, RestoreSeedFlow, RestoreBackupFlow
        import microns

        options = []

        if not self.temporary:
            options.append({'label': 'Create New Seed',
                            'value': lambda: NewSeedFlow(full_backup=True)})

        options.extend([{'label': 'Import Seed', 'value': lambda: RestoreSeedFlow(full_backup=True)},
                        {'label': 'Restore Backup', 'value': lambda: RestoreBackupFlow(full_backup=True)}])

        if not self.temporary:
            options.append({'label': 'Temporary Seed',
                            'value': lambda: InitialSeedSetupFlow(allow_backtrack=self.allow_backtrack,
                                                                  temporary=True)})

        flow = await ChooserPage(
            text=None,
            icon=lv.LARGE_ICON_SEED,
            options=options,
            left_micron=microns.Back).show()
        if flow is None:
            self.back()
            return

        result = await flow().run()
        if not result:
            return
        else:
            self.set_result(True)

    async def apply_external_key(self):
        from utils import spinner_task
        from tasks import save_seed_task
        from common import ui
        from pages import SuccessPage

        # Only allowed in temporary mode
        if not self.temporary:
            # TODO: add error messaging
            print("setting external key in permanent mode")
            self.set_result(False)
            return

        (error,) = await spinner_task('Saving seed', save_seed_task, args=[self.external_key])

        if error is not None:
            options.exit_temporary_mode()
            self.set_result(None)
            return

        await SuccessPage(text='Temporary seed applied.').show()

        ui.full_cards_refresh()
        await self.wait_to_die()
        self.set_result(True)
