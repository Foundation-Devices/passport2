# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# initial_seed_setup_flow.py - Menu to let user choose seed setup method

from flows.view_seed_words_flow import ViewSeedWordsFlow
import lvgl as lv
from flows import Flow


class InitialSeedSetupFlow(Flow):
    def __init__(self, is_envoy=True):
        super().__init__(initial_state=self.show_intro, name='InitialSeedSetupFlow')
        self.is_envoy = is_envoy

    async def show_intro(self):
        from pages import InfoPage
        from utils import has_seed
        import microns

        # Pass silently if seed already exists
        if has_seed():
            self.set_result(True)
            return

        result = await InfoPage(text='Next, let\'s create or restore a wallet seed.',
                                left_micron=None, right_micron=microns.Forward).show()
        if result:
            self.goto(self.show_seed_setup_menu)

    async def show_seed_setup_menu(self):
        from pages import OptionsChooserPage
        from flows import NewSeedFlow, RestoreSeedFlow, RestoreBackupFlow
        import microns

        options = [{'label': 'Restore Backup', 'value': lambda: RestoreBackupFlow()},
                   {'label': 'Restore Seed', 'value': lambda: RestoreSeedFlow()},
                   {'label': 'Create New Seed',
                    'value': lambda: NewSeedFlow(show_words=not self.is_envoy, full_backup=True)}]

        flow = await OptionsChooserPage(text=None, icon=lv.LARGE_ICON_SHIELD, options=options, default_idx=2,
                                        left_micron=microns.Back).show()
        if flow is None:
            self.back()
            return

        result = await flow().run()
        if not result:
            return
        else:
            self.set_result(True)
