# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# backup_code_section.py


import lvgl as lv
from micropython import const
from styles.colors import (
    BACKUP_CODE_SECTION_OUTLINE,
    BACKUP_CODE_DIGIT,
    BACKUP_CODE_DIGIT_FOCUSED,
    BACKUP_CODE_SECTION_BG,
    DIGIT_BORDER_COLOR_FOCUSED,
    DIGIT_BORDER_COLOR_UNFOCUSED)
from styles.local_style import LocalStyle
from views import View
from styles import Stylize
from views import Label
import passport

_NUM_DIGITS = const(4)
_HEIGHT = const(30)


class BackupCodeSection(View):

    def __init__(self, digits=[None] * _NUM_DIGITS, editable=True, focused_idx=None):
        super().__init__(flex_flow=lv.FLEX_FLOW.ROW)
        self.digits = digits
        self.digits_labels = []
        self.editable = editable
        self.focused_idx = focused_idx

        self.set_size(lv.pct(100), _HEIGHT)

        with Stylize(self) as default:
            default.flex_fill()
            default.radius(9)
            default.pad(top=4, bottom=4, left=10, right=10)

        with Stylize(self, selector=lv.STATE.FOCUS_KEY) as focus:
            focus.bg_color(BACKUP_CODE_SECTION_BG)
            focus.outline(width=2, color=BACKUP_CODE_SECTION_OUTLINE)

        for col in range(_NUM_DIGITS):
            container = View()
            container.set_height(lv.pct(100))
            container.set_no_scroll()

            with Stylize(container) as default:
                default.pad(left=4, right=4)
                default.flex_fill()
                default.border_width(2)
                default.border_side(lv.BORDER_SIDE.BOTTOM)
                default.bg_color(DIGIT_BORDER_COLOR_FOCUSED)
                default.bg_transparent()  # We go between transparent and not to show the bg color

                if not self.editable or self.focused_idx is None:
                    default.border_color(DIGIT_BORDER_COLOR_UNFOCUSED)
                else:
                    if passport.IS_COLOR:
                        default.bg_transparent()
                        if col == self.focused_idx:
                            default.border_color(DIGIT_BORDER_COLOR_FOCUSED)
                        else:
                            default.border_color(DIGIT_BORDER_COLOR_UNFOCUSED)
                    else:
                        if col == self.focused_idx:
                            default.bg_opaque()
                            default.radius(4)
                            default.border_side(lv.BORDER_SIDE.NONE)

            digit_text = str(self.digits[col]) if self.digits[col] is not None else ' '
            digit_label = Label(text=digit_text, color=BACKUP_CODE_DIGIT)
            with Stylize(digit_label) as default:
                default.align(lv.ALIGN.TOP_MID)
                if self.editable and self.focused_idx is not None:
                    if col == self.focused_idx:
                        default.text_color(BACKUP_CODE_DIGIT_FOCUSED)
            self.digits_labels.append(digit_label)

            container.set_children([digit_label])

            # Add the digit to the root
            self.add_child(container)

    def update_focused(self, prev_focused_idx):
        if prev_focused_idx is not None:
            # Set previous index to grey
            with LocalStyle(self.children[prev_focused_idx]) as prev:
                prev.bg_transparent()
                prev.border_color(DIGIT_BORDER_COLOR_UNFOCUSED)
                prev.border_side(lv.BORDER_SIDE.BOTTOM)

            with LocalStyle(self.digits_labels[prev_focused_idx]) as prev_label:
                prev_label.text_color(BACKUP_CODE_DIGIT)

        # Set new focus to blue if focused and mounted
        if self.focused_idx is not None:
            with LocalStyle(self.children[self.focused_idx]) as next:
                next.radius(4)
                if not passport.IS_COLOR:
                    next.border_side(lv.BORDER_SIDE.NONE)
                    next.bg_opaque()
                else:
                    next.border_color(DIGIT_BORDER_COLOR_FOCUSED)

            with LocalStyle(self.digits_labels[self.focused_idx]) as next_label:
                next_label.text_color(BACKUP_CODE_DIGIT_FOCUSED)

    def set_focused_idx(self, focused_idx):
        prev_focused_idx = self.focused_idx
        self.focused_idx = focused_idx
        self.update_focused(prev_focused_idx)

    def set_digits(self, digits):
        self.digits = digits
        if self.is_mounted():
            for col in range(_NUM_DIGITS):
                self.children[col].children[0].set_text(str(self.digits[col]) if self.digits[col] is not None else ' ')

    def focus(self, focused_idx):
        if self.is_mounted():
            self.add_state(lv.STATE.FOCUS_KEY)
            self.set_focused_idx(focused_idx)

    def defocus(self):
        if self.is_mounted():
            self.clear_state(lv.STATE.FOCUS_KEY)
            self.set_focused_idx(None)
