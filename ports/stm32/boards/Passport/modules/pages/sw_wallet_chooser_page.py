# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# sw_wallet_chooser_page.py - Chooser to select a specific softwre wallet to which to connect


from pages.chooser_page import ChooserPage


class SWWalletChooserPage(ChooserPage):
    def __init__(self, card_header={'title': 'Software Wallet'}, initial_value=None):
        from wallets.sw_wallets import supported_software_wallets

        options = []
        for wallet in supported_software_wallets:
            options.append({'label': wallet['label'], 'value': wallet})

        super().__init__(
            card_header=card_header,
            options=options,
            initial_value=initial_value or options[0].get('value'))
