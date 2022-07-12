# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# export_mode_chooser_page.py - Chooser to select export mode (e.g., QR vs. microSD)


from pages import ChooserPage


class ExportModeChooserPage(ChooserPage):
    def __init__(self, sw_wallet, card_header={'title': 'Export By'}, initial_value=None):
        options = []
        for export_mode in sw_wallet['export_modes']:
            options.append({'label': export_mode['label'], 'value': export_mode})

        super().__init__(
            card_header=card_header,
            options=options,
            initial_value=initial_value or options[0].get('value'))
