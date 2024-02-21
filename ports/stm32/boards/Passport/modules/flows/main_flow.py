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
        from utils import start_task, is_logged_in, has_seed, xfp2str, get_accounts
        from flows import SelectSetupModeFlow, LoginFlow, InitialSeedSetupFlow
        from extensions.extensions import supported_extensions

        await SelectSetupModeFlow().run()

        if not is_logged_in():
            await LoginFlow().run()

        if not has_seed():
            await InitialSeedSetupFlow(allow_backtrack=False).run()

        # TODO: consider using a "2.3.0 migrations" flag to skip all this after first run

        # Update old next_addrs keys to include the coin type and xfp
        next_addrs = common.settings.get('next_addrs', {})
        xfp = common.settings.get('xfp')
        string_xfp = xfp2str(xfp)
        for key in next_addrs:
            if "." not in key:  # new key format uses periods to prepend coin type and xfp
                next_addrs["0.{}.".format(string_xfp) + key] = next_addrs[key]
                del next_addrs[key]
        common.settings.set('next_addrs', next_addrs)

        # Update account settings to include the default xfp
        accounts = get_accounts()
        for account in accounts:
            if account.get('xfp', None) is None:
                account['xfp'] = xfp
        common.settings.set('accounts', accounts)

        # Update old extensions keys to include the xfp
        for extension in supported_extensions:
            old_key = 'ext.{}.{}'.format(extension['name'], 'enabled')
            if common.settings.get(old_key):
                common.settings.remove(old_key)
                common.settings.set(old_key + ".{}".format(string_xfp), True)

        common.settings.save()

        # Create initial cards by calling ui.update_cards()
        common.ui.update_cards(is_init=True)

        async def start_main_task():
            common.ui.start_card_task(card_idx=common.ui.active_card_idx)

        start_task(start_main_task())

        await self.wait_to_die()
