# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# shutdown_page.py - Ask user if they want to shutdown


import common
from pages import QuestionPage


class ShutdownPage(QuestionPage):
    def __init__(self):
        super().__init__(text='Shutdown Passport now?',)

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
