# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# auto_shutdown_setting_page.py - Set the auto-shutdown timeout

from pages import SettingPage


class AutoShutdownSettingPage(SettingPage):
    OPTIONS = [
        {'label': '1 minute', 'value': 1 * 60},
        {'label': '2 minutes', 'value': 2 * 60},
        {'label': '5 minutes', 'value': 5 * 60},
        {'label': '15 minutes', 'value': 15 * 60},
        {'label': '30 minutes', 'value': 30 * 60},
        {'label': '60 minutes', 'value': 60 * 60},
        {'label': 'Never', 'value': 0},
    ]

    def __init__(self, card_header=None, statusbar=None):
        super().__init__(
            card_header=card_header,
            statusbar=statusbar,
            setting_name='shutdown_timeout',
            options=self.OPTIONS,
            default_value=self.OPTIONS[2].get('value'))
