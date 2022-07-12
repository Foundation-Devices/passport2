# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# address_type_chooser_page.py - Chooser to select address type.


from pages import ChooserPage
from public_constants import AF_P2WPKH, AF_P2WPKH_P2SH, AF_CLASSIC


class AddressTypeChooserPage(ChooserPage):
    OPTIONS = [
        {'label': 'Native Segwit', 'value': AF_P2WPKH},
        {'label': 'P2SH-Segwit', 'value': AF_P2WPKH_P2SH},
        {'label': 'Legacy (P2PKH)', 'value': AF_CLASSIC},
    ]

    def __init__(self, card_header={'title': 'Address Type'}, initial_value=None):
        super().__init__(
            card_header=card_header,
            options=self.OPTIONS,
            initial_value=initial_value or self.OPTIONS[0].get('value'))
