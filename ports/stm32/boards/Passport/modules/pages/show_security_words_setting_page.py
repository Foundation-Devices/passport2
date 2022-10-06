# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# show_security_words_setting_page.py - Chooser to decide to show security words at login or not.


import lvgl as lv
from pages import SettingPage


class ShowSecurityWordsSettingPage(SettingPage):

    OPTIONS = [
        {'label': 'Show at Login', 'value': True},
        {'label': 'Don\'t Show', 'value': False}
    ]

    def __init__(self, card_header=None, statusbar=None):
        print("Here!")
        super().__init__(
            card_header=card_header,
            statusbar=statusbar,
            options=self.OPTIONS,
            setting_name='security_words',
            default_value=self.OPTIONS[1].get('value'),
            on_change=self.on_change
        )

    def on_change(self, selected_value):
        if selected_value is True:
            (pin, is_done) = await PINEntryPage(
                card_header={'title': 'Enter PIN'},
                security_words_message='Remember these Security Words',
                left_micron=microns.Back,
                right_micron=microns.Checkmark).show()
