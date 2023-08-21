# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# main_flow.py - Flow class to track position in a menu

from flows import Flow


class MainFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.start, name='MainFlow')

    async def start(self):
        import common
        from utils import start_task, is_logged_in, has_seed, xfp2str
        from flows import SelectSetupModeFlow, LoginFlow, InitialSeedSetupFlow

        await SelectSetupModeFlow().run()

        if not is_logged_in():
            await LoginFlow().run()

        if not has_seed():
            await InitialSeedSetupFlow(allow_backtrack=False).run()

        # Update old next_addrs keys to include the coin type and xfp
        next_addrs = common.settings.get('next_addrs', {})
        xfp = xfp2str(common.settings.get('xfp'))
        for key in next_addrs:
            if "." not in key:  # new key format uses periods to prepend coin type and xfp
                next_addrs["0.{}.".format(xfp) + key] = next_addrs[key]
                del next_addrs[key]

        # Create initial cards by calling ui.update_cards()
        common.ui.update_cards(is_init=True)

        async def start_main_task():
            common.ui.start_card_task(card_idx=common.ui.active_card_idx)

        start_task(start_main_task())

        await self.wait_to_die()
