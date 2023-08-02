# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# chain_setting_page.py - Set the current chain to Bitcoin mainnet or testnet

from pages.setting_page import SettingPage


class ChainSettingPage(SettingPage):
    OPTIONS = [
        {'label': 'Mainnet', 'value': 'BTC'},
        {'label': 'Testnet', 'value': 'TBTC'}
    ]

    def __init__(self, card_header=None, statusbar=None):
        super().__init__(
            card_header=card_header,
            statusbar=statusbar,
            setting_name='chain',
            options=self.OPTIONS,
            default_value=self.OPTIONS[0].get('value'))

    def save_setting(self, new_value):
        from common import settings

        settings.set_volatile(self.setting_name, new_value)

        try:
            # Refresh volatile XPB and XFP settings
            import stash
            with stash.SensitiveValues() as sv:
                sv.capture_xpub()
        except ValueError as e:
            # no secrets yet, not an error
            pass
