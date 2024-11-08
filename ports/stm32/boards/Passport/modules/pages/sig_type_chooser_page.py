# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# sig_type_chooser_page.py - Chooser to select signature type.


from pages import ChooserPage


class SigTypeChooserPage(ChooserPage):
    def __init__(self, sw_wallet, card_header={'title': 'Signature Type'}, initial_value=None):
        options = []
        for sig_type in sw_wallet['sig_types']:
            options.append({'label': sig_type['label'], 'value': sig_type})

        super().__init__(
            card_header=card_header,
            options=options,
            initial_value=initial_value or options[0].get('value'))
