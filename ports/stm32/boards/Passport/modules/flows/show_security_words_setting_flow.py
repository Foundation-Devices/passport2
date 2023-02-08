# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# show_security_words_setting_flow.py - Choose to decide to show security words at login or not.

import lvgl as lv
from flows import Flow
from pages import PINEntryPage, ShowSecurityWordsSettingPage
import microns


class ShowSecurityWordsSettingFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.select_setting, name='LoginFlow')

    async def select_setting(self):
        selected_value = await ShowSecurityWordsSettingPage().show()
        if selected_value:
            self.goto(self.enter_pin)
        else:
            self.set_result(None)

    async def enter_pin(self):
        (pin, is_done) = await PINEntryPage(
            card_header={'title': 'Enter PIN'},
            security_words_message='Remember these Security Words',
            check_pin_prefix=True,
            left_micron=microns.Back,
            right_micron=microns.Checkmark).show()
        if not is_done:
            self.back()
        else:
            # TODO: it would be good to check the pin
            self.set_result(True)
