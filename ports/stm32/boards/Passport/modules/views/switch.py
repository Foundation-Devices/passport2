# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# switch.py - An lvgl switch widget wrapper

import lvgl as lv
from views import View
from styles import Style
from styles.colors import SWITCH_BG_CHECKED, SWITCH_BG_UNCHECKED, SWITCH_BORDER, SWITCH_KNOB


class Switch(View):
    def __init__(self, value=False, on_change=None):
        super().__init__()
        self.value = value
        self.on_change = on_change

    def set_value(self, value):
        # print('Switch.set_value({})'.format(value))
        self.value = value
        if self.value:
            # print('Set to CHECKED')
            self.lvgl_root.add_state(lv.STATE.CHECKED)
        else:
            # print('Clear CHECKED')
            self.lvgl_root.clear_state(lv.STATE.CHECKED)

    def create_lvgl_root(self, lvgl_parent):
        return lv.switch(lvgl_parent)

    def mount(self, lvgl_parent):
        super().mount(lvgl_parent)

        default = Style()
        default.bg_transparent()
        default.apply(self.lvgl_root)

        knob = Style(selector=lv.PART.KNOB)
        knob.pad_all(-5)
        knob.bg_color(SWITCH_KNOB)
        knob.apply(self.lvgl_root)

        checked = Style(selector=lv.PART.INDICATOR | lv.STATE.CHECKED)
        checked.bg_color(SWITCH_BG_CHECKED)
        checked.border_width(2)
        checked.border_color(SWITCH_BORDER)
        checked.apply(self.lvgl_root)

        unchecked = Style(selector=lv.PART.INDICATOR)
        unchecked.bg_color(SWITCH_BG_UNCHECKED)
        unchecked.border_width(2)
        unchecked.border_color(SWITCH_BORDER)
        unchecked.apply(self.lvgl_root)

        if self.value:
            self.lvgl_root.add_state(lv.STATE.CHECKED)

    def attach(self, group):
        super().attach(group)
        self.lvgl_root.add_event_cb(self.on_change, lv.EVENT.VALUE_CHANGED, None)

    def detach(self):
        self.lvgl_root.remove_event_cb(self.on_change)
        super().detach()
