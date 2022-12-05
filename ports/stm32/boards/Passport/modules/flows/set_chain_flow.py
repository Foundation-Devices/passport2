# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# set_chain_flow.py - Set the chain to testnet or mainnet, then if testnet was chosen, show a warning

import lvgl as lv
from flows import Flow
from pages import ChainSettingPage, ErrorPage


class SetChainFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.show_setting_page, name='SetChainFlow')
        self.result = None

    async def show_setting_page(self):
        from common import ui

        self.result = await ChainSettingPage(card_header={'title': 'Network', 'icon': lv.ICON_NETWORK}).show()
        if self.result is 'TBTC':
            self.goto(self.show_testnet_warning)
        else:
            self.set_result(self.result)

    async def show_testnet_warning(self):
        from common import ui

        await ErrorPage(
            'Passport is in Testnet mode. Use a separate seed to avoid issues with malicious software wallets.').show()

        self.set_result(self.result)
