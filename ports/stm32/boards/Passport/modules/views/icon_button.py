# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# icon_button.py - A recolorable icon view

import lvgl as lv
from styles.style import Stylize
from views import View, Icon
from styles.colors import MEDIUM_GREY

PRESS_Y_OFFSET = 3


class IconButton(View):
    def __init__(self, icon, color=MEDIUM_GREY, opa=255):
        super().__init__()
        self.icon = icon
        self.color = color
        self.pressed_color = self.color.color_darken(100)
        self.opa = opa

        self.set_size(icon.header.w, icon.header.h + PRESS_Y_OFFSET)

        with Stylize(self, selector=lv.STATE.PRESSED) as pressed:
            pressed.pad(top=PRESS_Y_OFFSET)

        self.icon = Icon(icon=self.icon, color=color, opa=opa)
        with Stylize(self.icon, selector=lv.STATE.PRESSED) as pressed:
            pressed.img_recolor(self.pressed_color, self.opa)

        self.add_child(self.icon)

    def set_color(self, color=None, opa=None):
        # print('IconButton.set_color(color={}, opa={}'.format(color, opa))
        self.icon.set_color(color=color, opa=opa)

    def set_pressed(self, is_pressed=True):
        if self.is_mounted():
            if is_pressed:
                self.add_state(lv.STATE.PRESSED)
                self.icon.add_state(lv.STATE.PRESSED)
            else:
                self.clear_state(lv.STATE.PRESSED)
                self.icon.clear_state(lv.STATE.PRESSED)
