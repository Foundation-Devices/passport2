# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# slider.py - Wrapper over the lvgl slider widget

import lvgl as lv
from styles import Stylize
from styles.colors import DARK_GREY, LIGHT_GREY
from views import View


class Slider(View):
    def __init__(self, range, initial_value=0, knob_color=None, track_color=None, on_change=None):
        super().__init__()
        self.range = range
        self.initial_value = initial_value
        self.knob_color = knob_color
        self.track_color = track_color
        self.on_change = on_change

        if knob_color is not None:
            with Stylize(self, lv.PART.KNOB) as knob:
                knob.bg_color(knob_color)

        if track_color is not None:
            with Stylize(self, selector=lv.PART.MAIN) as track:
                track.bg_color(LIGHT_GREY)

            with Stylize(self, selector=lv.STATE.FOCUS_KEY) as focus:
                focus.outline(width=2, color=DARK_GREY)

            with Stylize(self, selector=lv.PART.INDICATOR) as track:
                track.bg_color(track_color)

    def create_lvgl_root(self, lvgl_parent):
        return lv.slider(lvgl_parent)

    def attach(self, group):
        super().attach(group)
        self.lvgl_root.set_range(*self.range)
        self.lvgl_root.set_value(self.initial_value, False)
        if self.on_change is not None:
            self.lvgl_root.add_event_cb(
                lambda e: self.on_change(self.lvgl_root.get_value()),
                lv.EVENT.VALUE_CHANGED, None)

    def detach(self, ):
        if self.on_change is not None:
            self.lvgl_root.remove_event_cb(self.on_change)
        # lv.group_remove_obj(self.lvgl_root)
        super().detach()

    def on_change(self, value):
        value = self.lvgl_root.get_value()
