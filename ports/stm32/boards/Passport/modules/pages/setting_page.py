# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# setting_page.py - A ChooserPage that can get the current value from settings and save it to settings.

from pages.chooser_page import ChooserPage


class SettingPage(ChooserPage):
    def __init__(self, card_header=None, statusbar=None, options=[],
                 setting_name=None, default_value=None, on_change=None, scroll_fix=False):
        self.setting_name = setting_name
        self.default_value = default_value

        super().__init__(
            card_header=card_header,
            statusbar=statusbar,
            options=options,
            initial_value=self.get_setting(),
            on_change=self._on_setting_change,
            scroll_fix=scroll_fix)

        self.on_setting_change = on_change

    def _on_setting_change(self, selected_value):
        if self.setting_name is not None:
            self.save_setting(selected_value)

        if self.on_setting_change is not None:
            self.on_setting_change(selected_value)

    def get_setting(self):
        from common import settings

        return settings.get(self.setting_name, self.default_value)

    def save_setting(self, new_value):
        from common import settings

        # print('SettingPage.save_setting() !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
        settings.set(self.setting_name, new_value)
