# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# main_flow.py - Flow class to track position in a menu

from flows import Flow
from flows.update_firmware_flow import UpdateFirmwareFlow

AUTOINSTALL_LOOP = True


class MainFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.start, name='MainFlow')

    async def start(self):
        import common
        from utils import start_task, is_logged_in, has_seed
        from flows import SelectSetupModeFlow, LoginFlow, InitialSeedSetupFlow

        # Automated testing for firmware updates
        if AUTOINSTALL_LOOP:
            from files import CardSlot
            from pages import ErrorPage

            print('AutoLogin: 111111...')
            await LoginFlow(auto_pin='111111').run()

            update_file_path = CardSlot.get_sd_root() + '/' + 'v2.0.4-dev-passport.bin'
            print('AutoUpdate: {}...'.format(update_file_path))
            await UpdateFirmwareFlow(update_file_path=update_file_path).run()

            await ErrorPage(text='AUTOINSTALL LOOP SHOULD NEVER GET HERE!').show()

        await SelectSetupModeFlow().run()

        if not is_logged_in():
            await LoginFlow().run()

        if not has_seed():
            await InitialSeedSetupFlow().run()

        # Create initial cards by calling ui.update_cards()
        common.ui.update_cards(is_init=True)

        async def start_main_task():
            common.ui.start_card_task(card_idx=common.ui.active_card_idx)

        start_task(start_main_task())

        await self.wait_to_die()
