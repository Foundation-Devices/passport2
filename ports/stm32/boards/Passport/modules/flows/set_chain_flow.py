# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# set_chain_flow.py - Set the chain to testnet or mainnet, then if testnet was chosen, show a warning

import lvgl as lv
from flows import Flow
from pages import ChainSettingPage, ErrorPage


class SetChainFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.show_setting_page, name='SetChainFlow')

    async def show_setting_page(self):
        network = await ChainSettingPage(card_header={'title': 'Network', 'icon': 'ICON_NETWORK'}).show()

        if network is 'TBTC':
            text = "Passport is in Testnet mode. Use a separate seed to avoid issues " \
                   "with malicious software wallets."
            await ErrorPage(text).show()

        self.set_result(network)
