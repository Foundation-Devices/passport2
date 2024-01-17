# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# address_type_chooser_page.py - Chooser to select address type.


from pages import ChooserPage
from public_constants import AF_P2WPKH, AF_P2WPKH_P2SH, AF_CLASSIC, AF_P2TR


class AddressTypeChooserPage(ChooserPage):
    OPTIONS = [
        {'label': 'Segwit', 'value': AF_P2WPKH},
        {'label': 'Wrapped Segwit', 'value': AF_P2WPKH_P2SH},
        {'label': 'Legacy', 'value': AF_CLASSIC},
        {'label': 'Taproot', 'value': AF_P2TR},
    ]

    def __init__(self, card_header={'title': 'Address Type'}, initial_value=None,
                 left_micron=None, right_micron=None):
        super().__init__(
            card_header=card_header,
            options=self.OPTIONS,
            initial_value=initial_value or self.OPTIONS[0].get('value'),
            left_micron=left_micron,
            right_micron=right_micron)
