# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# label.py - Basic label with multiple wrapping behaviors


import lvgl as lv
from views import View
from styles import Stylize, FONT_NORMAL


class Label(View):
    def __init__(self, text='', color=None, font=FONT_NORMAL, long_mode=lv.label.LONG.WRAP, center=False, recolor=True,
                 text_align=None):
        super().__init__()
        self.text = text
        self.color = color
        self.font = font
        self.long_mode = long_mode
        self.center = center
        self.recolor = recolor
        self.text_align = text_align

        with Stylize(self) as default:
            default.font(self.font)
            if self.color is not None:
                default.text_color(self.color)
            if center:
                default.text_align(lv.TEXT_ALIGN.CENTER)
            elif text_align is not None:
                default.text_align(self.text_align)

    def set_text(self, text):
        self.text = text
        if self.is_mounted():
            self.lvgl_root.set_text(text)

    def set_long_mode(self, long_mode):
        self.long_mode = long_mode
        if self.is_mounted():
            self.lvgl_root.set_long_mode(long_mode)

    def create_lvgl_root(self, lvgl_parent):
        return lv.label(lvgl_parent)

    def mount(self, lvgl_parent):
        super().mount(lvgl_parent)

        self.lvgl_root.set_text(self.text)
        self.lvgl_root.set_long_mode(self.long_mode)
        self.lvgl_root.set_recolor(self.recolor)

        return self.lvgl_root
