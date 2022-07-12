# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# backup_code_section.py


import lvgl as lv
from styles.colors import FD_BLUE, LIGHT_GREY, TEXT_GREY, VERY_LIGHT_GREY
from styles.local_style import LocalStyle
from views import View
from styles import Stylize
from views import Label

NUM_DIGITS = 4
HEIGHT = 30
DIGIT_BORDER_COLOR_UNFOCUSED = LIGHT_GREY
DIGIT_BORDER_COLOR_FOCUSED = FD_BLUE


class BackupCodeSection(View):

    def __init__(self, digits=[None] * NUM_DIGITS, editable=True, focused_idx=None):
        super().__init__(flex_flow=lv.FLEX_FLOW.ROW)
        self.digits = digits
        self.editable = editable
        self.focused_idx = focused_idx

        self.set_size(lv.pct(100), HEIGHT)

        with Stylize(self) as default:
            default.flex_fill()
            default.radius(9)
            default.pad(top=4, bottom=4, left=10, right=10)

        with Stylize(self, selector=lv.STATE.FOCUS_KEY) as focus:
            focus.bg_color(VERY_LIGHT_GREY)
            focus.outline(width=2, color=FD_BLUE)

        for col in range(NUM_DIGITS):
            container = View()
            container.set_height(lv.pct(100))
            container.set_no_scroll()

            with Stylize(container) as default:
                default.pad(left=4, right=4)
                default.flex_fill()
                default.border_width(2)
                default.border_side(lv.BORDER_SIDE.BOTTOM)
                if not self.editable or self.focused_idx is None:
                    default.border_color(DIGIT_BORDER_COLOR_UNFOCUSED)
                else:
                    default.border_color(DIGIT_BORDER_COLOR_FOCUSED if col ==
                                         self.focused_idx else DIGIT_BORDER_COLOR_UNFOCUSED)

            digit_text = str(self.digits[col]) if self.digits[col] is not None else ' '
            digit = Label(text=digit_text, color=TEXT_GREY)
            with Stylize(digit) as default:
                default.align(lv.ALIGN.TOP_MID)

            container.set_children([digit])

            # Add the digit to the root
            self.add_child(container)

    def update_focused(self, prev_focused_idx):
        if prev_focused_idx is not None:
            # Set previous index to grey
            with LocalStyle(self.children[prev_focused_idx]) as prev:
                prev.border_color(DIGIT_BORDER_COLOR_UNFOCUSED)
                # prev.bg_color(WHITE, opa=0)

        # Set new focus to blue if focused and mounted
        if self.focused_idx is not None:
            focus_color = DIGIT_BORDER_COLOR_UNFOCUSED
            if self.is_mounted() and self.lvgl_root.get_state() & lv.STATE.FOCUS_KEY:
                focus_color = DIGIT_BORDER_COLOR_FOCUSED

            with LocalStyle(self.children[self.focused_idx]) as new:
                new.border_color(focus_color)
                # new.bg_color(focus_color)

    def set_focused_idx(self, focused_idx):
        prev_focused_idx = self.focused_idx
        self.focused_idx = focused_idx
        self.update_focused(prev_focused_idx)

    def set_digits(self, digits):
        self.digits = digits
        if self.is_mounted():
            for col in range(NUM_DIGITS):
                self.children[col].children[0].set_text(str(self.digits[col]) if self.digits[col] is not None else ' ')

    def focus(self, focused_idx):
        if self.is_mounted():
            self.add_state(lv.STATE.FOCUS_KEY)
            self.set_focused_idx(focused_idx)

    def defocus(self):
        if self.is_mounted():
            self.clear_state(lv.STATE.FOCUS_KEY)
            self.set_focused_idx(None)
