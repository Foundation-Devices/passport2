# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# initial_seed_setup_flow.py - Menu to let user choose seed setup method

from flows.flow import Flow


class InitialSeedSetupFlow(Flow):
    def __init__(self, is_envoy=True, allow_backtrack=True):
        super().__init__(initial_state=self.show_intro, name='InitialSeedSetupFlow')
        self.is_envoy = is_envoy
        self.statusbar = {'title': 'CREATE SEED', 'icon': 'ICON_SEED'}
        self.allow_backtrack = allow_backtrack

    async def show_intro(self):
        from pages.info_page import InfoPage
        from utils import has_seed
        import microns
        import lvgl as lv

        # Pass silently if seed already exists
        if has_seed():
            self.set_result(True)
            return

        if self.allow_backtrack:
            left_micron = microns.Back
        else:
            left_micron = None

        result = await InfoPage(
            icon=lv.LARGE_ICON_SEED,
            text='Next, let\'s create or restore a wallet seed.',
            left_micron=left_micron, right_micron=microns.Forward).show()
        if result:
            self.goto(self.show_seed_setup_menu)
        else:
            self.set_result(None)

    async def show_seed_setup_menu(self):
        from pages.chooser_page import ChooserPage
        from flows import NewSeedFlow, RestoreSeedFlow, RestoreBackupFlow
        import microns
        import lvgl as lv

        options = [{'label': 'Create New Seed',
                    'value': lambda: NewSeedFlow(show_words=not self.is_envoy, full_backup=True)},
                   {'label': 'Restore Seed', 'value': lambda: RestoreSeedFlow(full_backup=True)},
                   {'label': 'Restore Backup', 'value': lambda: RestoreBackupFlow(full_backup=True)}]

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
