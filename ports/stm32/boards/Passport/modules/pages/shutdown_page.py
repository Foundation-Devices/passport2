# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# shutdown_page.py - Ask user if they want to shutdown

import lvgl as lv
from styles.colors import DEFAULT_LARGE_ICON_COLOR
import common
from pages import QuestionPage


class ShutdownPage(QuestionPage):
    def __init__(self, icon=lv.LARGE_ICON_QUESTION, icon_color=DEFAULT_LARGE_ICON_COLOR, text='Shutdown Passport now?'):
        super().__init__(icon=icon, icon_color=icon_color, text=text)

    def attach(self, group):
        super().attach(group)
        common.keypad.enable_global_nav_keys(False)

    def detach(self):
        common.keypad.enable_global_nav_keys(True)
        super().detach()

    def left_action(self, is_pressed):
        if not is_pressed:
            self.set_result(None)

    def right_action(self, is_pressed):
        if not is_pressed:
            common.system.shutdown()
