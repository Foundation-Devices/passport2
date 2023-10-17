# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# address_type_chooser_page.py - Chooser to select address type.


from pages import ChooserPage
from public_constants import AF_P2WPKH, AF_P2WPKH_P2SH, AF_CLASSIC, AF_P2TR


class AddressTypeChooserPage(ChooserPage):
    LABELS = {
        AF_P2WPKH: 'Segwit',
        AF_P2WPKH_P2SH: 'Wrapped Segwit',
        AF_CLASSIC: 'Legacy',
        AF_P2TR: 'Taproot',
    }

    def __init__(self, card_header={'title': 'Address Type'}, initial_value=None, options=None):

        if options is None:
            options = list(self.LABELS.keys())

        final_options = []
        for addr_type in options:
            final_options.append({'label': self.LABELS[addr_type], 'value': addr_type})

        super().__init__(
            card_header=card_header,
            options=final_options,
            initial_value=initial_value or final_options[0].get('value'))
