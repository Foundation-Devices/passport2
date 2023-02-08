# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# symbol_picker.py - View to display a grid of symbols to the user and let them select one

import lvgl as lv
from styles.style import Stylize
from views import View
from views import Label
from styles.colors import FD_BLUE, WHITE, LIGHT_GREY, NORMAL_TEXT, SYMBOL_PICKER_TEXT
from constants import MENU_ITEM_CORNER_RADIUS
import passport


class SymbolPicker(View):
    symbols = [
        '!@#$%^&*',
        '+/-=\\?|~',
        '_"`\',.:;',
        '()[]{}<>',
    ]

    def __init__(self):
        super().__init__(flex_flow=lv.FLEX_FLOW.COLUMN)
        self.row = 0
        self.col = 0

        self.set_size(lv.pct(100), lv.SIZE.CONTENT)

        with Stylize(self) as default:
            default.radius(MENU_ITEM_CORNER_RADIUS)
            default.bg_color(LIGHT_GREY)
            default.pad_all(8)
            default.pad_col(4)
            default.flex_align(cross=lv.FLEX_ALIGN.CENTER)

        # Add symbols
        for row in range(len(self.symbols)):
            symbols = self.symbols[row]
            label_row = View(flex_flow=lv.FLEX_FLOW.ROW)
            label_row.set_size(lv.pct(100), lv.SIZE.CONTENT)
            with Stylize(label_row) as default:
                default.flex_align(main=lv.FLEX_ALIGN.SPACE_BETWEEN)

            for col in range(len(symbols)):
                symbol = symbols[col]
                label = Label(text=symbol, color=SYMBOL_PICKER_TEXT, recolor=False)
                if not passport.IS_COLOR:
                    with Stylize(label) as default:
                        default.pad_all(2)

                label_row.add_child(label)
                if passport.IS_COLOR:
                    with Stylize(label, selector=lv.STATE.FOCUS_KEY) as focus:
                        focus.text_color(FD_BLUE)
                else:
                    with Stylize(label, selector=lv.STATE.FOCUS_KEY) as focus:
                        focus.pad_all(2)
                        focus.radius(4)
                        focus.text_color(NORMAL_TEXT)
                        focus.bg_color(WHITE)

            self.add_child(label_row)

    def attach(self, group):
        super().attach(group)
        self.update_cursor(row=self.row, col=self.col)

    def update_cursor(self, row=None, col=None):
        if self.is_mounted():
            # Clear the highlight from the old symbol
            curr_label = self.children[self.row].children[self.col]
            curr_label.lvgl_root.clear_state(lv.STATE.FOCUS_KEY)

            if row is not None:
                self.row = row
            if col is not None:
                self.col = col

            # Highlight the new symbol
            label = self.children[self.row].children[self.col]
            label.lvgl_root.add_state(lv.STATE.FOCUS_KEY)

    def cursor_left(self):
        if self.col > 0:
            self.update_cursor(col=self.col - 1)

    def cursor_right(self):
        symbols = self.children[self.row].children
        if self.col < len(symbols) - 1:
            self.update_cursor(col=self.col + 1)

    def cursor_up(self):
        if self.row > 0:
            self.update_cursor(row=self.row - 1)

    def cursor_down(self):
        if self.row < len(self.children) - 1:
            self.update_cursor(row=self.row + 1)

    def get_selected_symbol(self):
        return SymbolPicker.symbols[self.row][self.col]
