# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# bold_label.py - Bold label (drawn twice with offsets))


import lvgl as lv
from styles.style import Stylize
from styles.colors import BLACK, WHITE
from views import View, Label
from styles import FONT_NORMAL
import passport


class BoldLabel(View):
    def __init__(self, text='', color=None, font=FONT_NORMAL, center=False, long_mode=lv.label.LONG.WRAP):
        super().__init__()
        self.center = center
        self.labels = []

        self.set_size(lv.SIZE.CONTENT, lv.SIZE.CONTENT)
        if passport.IS_COLOR:
            for x, y in [(0, 0), (1, 1)]:
                self.add_label(x, y, text, color, font, long_mode)
        else:
            if color == BLACK:
                rev_color = WHITE
            else:
                rev_color = BLACK

            # Add the outline labels
            for y in range(-1, 2):
                for x in range(-1, 2):
                    if not (x == 0 and y == 0):
                        self.add_label(x * 2, y * 2, text, rev_color, font, long_mode)

            # Add the main label
            self.add_label(0, 0, text, color, font, long_mode)

        self.set_no_scroll()

        self.set_children(self.labels)

    def add_label(self, x, y, text, color, font, long_mode):
        label = Label(text=text, color=color, font=font, long_mode=long_mode)
        label.set_pos(x, y)
        if self.center:
            with Stylize(label) as default:
                default.align(lv.ALIGN.CENTER)
        self.labels.append(label)

    def set_text(self, text):
        for y in range(-1, 2):
            for x in range(-1, 2):
                self.labels[y * 2 + x].set_text(text)

    def set_long_mode(self, long_mode):
        for y in range(-1, 2):
            for x in range(-1, 2):
                self.labels[y * 2 + x].set_long_mode(long_mode)
