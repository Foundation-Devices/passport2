# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# seed_length_chooser_page.py - Chooser to select seed length to restore/create.


from pages import ChooserPage


class SeedLengthChooserPage(ChooserPage):
    OPTIONS = [
        {'label': '24 words', 'value': 24},
        {'label': '18 words', 'value': 18},
        {'label': '12 words', 'value': 12},
    ]

    def __init__(self, card_header={'title': 'Seed Length'}, initial_value=None):
        super().__init__(
            card_header=card_header,
            options=self.OPTIONS,
            initial_value=initial_value or self.OPTIONS[0].get('value'))
