# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# keyboard.py - Wrapper for the lvgl keyboard widget

import lvgl as lv
from views import View


class Keyboard(View):
    def __init__(self, keymap=None):
        super().__init__()
        self.keymap = keymap

    def create_lvgl_root(self, lvgl_parent):
        keyboard = lv.keyboard(lvgl_parent)
        # TODO: Customize keymap
        return keyboard
