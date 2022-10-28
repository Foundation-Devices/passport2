# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# main_flow.py - Flow class to track position in a menu

from flows import Flow


class MainFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.start, name='MainFlow')

    async def start(self):
        import common
        from utils import start_task, is_logged_in, has_seed
        from flows import SelectSetupModeFlow, LoginFlow, InitialSeedSetupFlow, BackupFlow

        await SelectSetupModeFlow().run()

        if not is_logged_in():
            await LoginFlow().run()

        if not has_seed():
            await InitialSeedSetupFlow(allow_backtrack=False).run()

        if not common.settings.get('backup_quiz', False):
            await BackupFlow().run()

        # Create initial cards by calling ui.update_cards()
        common.ui.update_cards(is_init=True)

        async def start_main_task():
            common.ui.start_card_task(card_idx=common.ui.active_card_idx)

        start_task(start_main_task())

        await self.wait_to_die()
