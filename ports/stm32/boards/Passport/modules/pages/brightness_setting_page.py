# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# brightness_setting_page.py - Set the screen brightness and save it


from pages import SettingPage
from utils import get_screen_brightness, set_screen_brightness
import passport
import common


class BrightnessSettingPage(SettingPage):
    OPTIONS = [
        {'label': '5%', 'value': 5},
        {'label': '25%', 'value': 25},
        {'label': '50%', 'value': 50},
        {'label': '75%', 'value': 75},
        {'label': '100%', 'value': 100}
    ]

    def __init__(self, card_header=None, statusbar=None):
        super().__init__(
            card_header=card_header,
            statusbar=statusbar,
            setting_name='screen_brightness',  # NOTE: Not actually used for this setting as we store it in EEPROM
            options=self.OPTIONS,
            default_value=self.OPTIONS[4].get('value'),
            on_change=self.on_change,
            scroll_fix=not passport.IS_COLOR)

    def on_change(self, new_value):
        common.display.set_brightness(new_value)

    def get_setting(self):
        return get_screen_brightness(self.default_value)

    def save_setting(self, new_value):
        set_screen_brightness(new_value)
