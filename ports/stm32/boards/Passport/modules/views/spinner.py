# SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# spinner.py - Wrapper around LVLG spinner component


import lvgl as lv
from views import View
from styles.colors import DEFAULT_SPINNER, SPINNER_BG
import passport


class Spinner(View):
    def __init__(self, width=7, color=DEFAULT_SPINNER):
        super().__init__()
        self.arc_width = width
        self.arc_color = color

    def create_lvgl_root(self, lvgl_parent):
        return lv.spinner(lvgl_parent, 1000, 60)

    def mount(self, lvgl_parent):
        super().mount(lvgl_parent)

        # Arc indicator
        self.lvgl_root.set_style_arc_color(self.arc_color, lv.PART.INDICATOR)
        self.lvgl_root.set_style_arc_width(self.arc_width, lv.PART.INDICATOR)

        self.lvgl_root.set_style_arc_color(SPINNER_BG, lv.PART.MAIN)
        self.lvgl_root.set_style_arc_width(self.arc_width, lv.PART.MAIN)

        # Knob
        # Weird, but pad of -1 makes the knob look better
        self.lvgl_root.set_style_pad_all(-1, lv.PART.KNOB)
        self.lvgl_root.set_style_bg_color(self.arc_color, lv.PART.KNOB)
