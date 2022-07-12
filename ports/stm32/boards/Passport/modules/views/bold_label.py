# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# bold_label.py - Bold label (drawn twice with offsets))


import lvgl as lv
from styles.style import Stylize
from views import View, Label
from styles import FONT_NORMAL


class BoldLabel(View):
    def __init__(self, text='', color=None, font=FONT_NORMAL, center=False, long_mode=lv.label.LONG.WRAP):
        super().__init__()
        self.center = center

        self.set_size(lv.SIZE.CONTENT, lv.SIZE.CONTENT)
        self.label1 = Label(text=text, color=color, font=font, long_mode=long_mode)
        self.label2 = Label(text=text, color=color, font=font, long_mode=long_mode)
        self.label2.set_pos(1, 1)
        self.set_no_scroll()

        if self.center:
            with Stylize(self.label1) as default:
                default.align(lv.ALIGN.CENTER)
            with Stylize(self.label2) as default:
                default.align(lv.ALIGN.CENTER)

        self.set_children([self.label1, self.label2])

    def set_text(self, text):
        self.label1.set_text(text)
        self.label2.set_text(text)

    def set_long_mode(self, long_mode):
        self.label1.set_long_mode(long_mode)
        self.label2.set_long_mode(long_mode)
