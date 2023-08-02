# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# setup_mode_chooser_page.py - Chooser to select address type.

from pages.chooser_page import ChooserPage
import microns


class SetupModeChooserPage(ChooserPage):
    OPTIONS = [
        {'label': 'Envoy App', 'value': 'envoy'},
        {'label': 'Manual Setup', 'value': 'manual'}
    ]

    def __init__(self, left_micron=microns.Back):
        import lvgl as lv

        super().__init__(
            options=self.OPTIONS,
            icon=lv.LARGE_ICON_SETUP,
            text='How would you like to\nset up your Passport?',
            center=True,
            item_icon=None,
            initial_value=self.OPTIONS[0].get('value'),
            left_micron=left_micron)
