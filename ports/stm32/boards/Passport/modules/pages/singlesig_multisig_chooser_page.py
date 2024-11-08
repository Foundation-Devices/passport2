# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# singlesig_multisig_chooser_page.py - Chooser to select singlesig or a specific multisig config


from pages import ChooserPage


class SinglesigMultisigChooserPage(ChooserPage):
    def __init__(self, multisigs, card_header={'title': 'Single/Multisig'}, initial_value=None,
                 left_micron=None, right_micron=None):
        options = [{'label': 'Single-sig', 'value': ('single-sig', None)}]

        for ms in multisigs:
            label = '%d/%d: %s' % (ms.M, ms.N, ms.name)
            options.append({'label': label, 'value': ('multisig', ms)})

        super().__init__(
            card_header=card_header,
            options=options,
            initial_value=initial_value or options[0].get('value'),
            left_micron=left_micron,
            right_micron=right_micron)
