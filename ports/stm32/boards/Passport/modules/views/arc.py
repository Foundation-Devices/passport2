# SPDX-FileCopyrightText: 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# arc.py - Wrapper around lv.arc


import lvgl as lv
from styles.colors import FD_BLUE, SPINNER_BG
from views import View


class Arc(View):
    def __init__(self, start=0, end=0, width=7, color=FD_BLUE, rotation=270):
        super().__init__()
        self.start = start
        self.end = end
        self.arc_width = width
        self.arc_color = color
        self.rotation = rotation

    def create_lvgl_root(self, lvgl_parent):
        return lv.arc(lvgl_parent)

    def mount(self, lvgl_parent):
        super().mount(lvgl_parent)

        # Geometry
        self.lvgl_root.set_rotation(self.rotation)
        self.lvgl_root.set_angles(self.start, self.end)
        self.lvgl_root.set_bg_angles(0, 360)

        # Arc indicator
        self.lvgl_root.set_style_arc_color(self.arc_color, lv.PART.INDICATOR)
        self.lvgl_root.set_style_arc_width(self.arc_width, lv.PART.INDICATOR)

        self.lvgl_root.set_style_arc_color(SPINNER_BG, lv.PART.MAIN)
        self.lvgl_root.set_style_arc_width(self.arc_width, lv.PART.MAIN)

        # Knob
        # Weird, but pad of -1 makes the knob look better
        self.lvgl_root.set_style_pad_all(-1, lv.PART.KNOB)
        self.lvgl_root.set_style_bg_color(self.arc_color, lv.PART.KNOB)

        return self.lvgl_root

    def set_start_angle(self, start):
        self.start = start
        if self.is_mounted():
            self.lvgl_root.set_start_angle(self.start)

    def set_end_angle(self, end):
        self.end = end
        if self.is_mounted():
            self.lvgl_root.set_end_angle(self.start)
