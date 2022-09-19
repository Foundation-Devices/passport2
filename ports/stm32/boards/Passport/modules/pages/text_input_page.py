# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# text_input_page.py

import lvgl as lv
from styles.colors import NORMAL_TEXT
from utils import InputMode
from pages import Page
from views import Label, TextInput, SymbolPicker
from styles import Stylize
from t9 import T9
from keys import KEY_1
import microns
import passport


class TextInputPage(Page):
    def __init__(self,
                 title=None,
                 initial_text='',
                 initial_mode=InputMode.UPPER_ALPHA,
                 max_length=64,
                 numeric_only=False,
                 max_value=2_147_483_646,
                 card_header=None,
                 statusbar=None,
                 left_micron=microns.Back,
                 right_micron=microns.Checkmark):
        super().__init__(card_header=card_header,
                         statusbar=statusbar,
                         left_micron=left_micron,
                         right_micron=right_micron)
        self.title = title
        self.text = initial_text
        self.is_showing_symbols = False
        self.symbol_picker = None
        self.numeric_only = numeric_only
        if self.numeric_only:
            # Force to numeric input mode
            initial_mode = InputMode.NUMERIC

        self.t9 = T9(text=self.text,
                     cursor_pos=len(self.text),
                     mode=initial_mode,
                     numeric_only=self.numeric_only,
                     max_length=max_length)

        self.set_no_scroll()
        with Stylize(self) as default:
            default.pad(left=0, right=0)
            if not passport.IS_COLOR:
                default.pad_row(4)

        # TODO: Replace with built-in Card Title?
        if self.title is not None:
            self.title_view = Label(text=self.title, color=NORMAL_TEXT)
            self.title_view.set_width(lv.pct(100))
            with Stylize(self.title_view) as default:
                default.pad(top=20)
                default.text_align(lv.TEXT_ALIGN.CENTER)
            self.add_child(self.title_view)

        self.input = TextInput(text=self.text, input_mode=initial_mode)
        self.input.set_width(lv.pct(100))
        self.add_child(self.input)

    def right_action(self, is_pressed):
        if not is_pressed:
            if self.is_showing_symbols:
                ch = self.symbol_picker.get_selected_symbol()
                self.t9.insert(ch)
                self.is_showing_symbols = False
                self.t9.set_mode(self.last_input_mode)
                self.synchronize_with_t9()
                self.update_symbol_picker()
                return
            text = self.input.get_text()
            self.set_result(text)

    def left_action(self, is_pressed):
        if not is_pressed:
            self.set_result(None)

    def attach(self, group):
        super().attach(group)
        group.add_obj(self.lvgl_root)
        self.lvgl_root.add_event_cb(self.on_key, lv.EVENT.KEY, None)

        self.update_symbol_picker()

    def detach(self):
        self.lvgl_root.remove_event_cb(self.on_key)
        lv.group_remove_obj(self.lvgl_root)
        super().detach()

    def update_symbol_picker(self):
        if self.is_mounted():
            if self.symbol_picker is not None:
                self.symbol_picker.detach()
                self.symbol_picker.unmount()
                self.symbol_picker = None

            if self.is_showing_symbols:
                self.symbol_picker = SymbolPicker()
                self.add_child(self.symbol_picker)
                self.symbol_picker.mount(self.lvgl_root)
                self.symbol_picker.attach(self.group)

    def synchronize_with_t9(self):
        self.text = self.t9.get_text()
        self.input.set_text(self.text)
        self.input.set_mode(self.t9.mode)
        self.input.set_cursor_pos(self.t9.cursor_pos)

    def on_key(self, event):
        key = event.get_key()

        if self.t9.mode != InputMode.NUMERIC and key == KEY_1:
            self.is_showing_symbols = not self.is_showing_symbols
            self.update_symbol_picker()
            if self.is_showing_symbols:
                self.last_input_mode = self.t9.mode
                self.t9.set_mode(InputMode.PUNCTUATION)
            else:
                self.t9.set_mode(self.last_input_mode)
            self.synchronize_with_t9()
            return

        if self.is_showing_symbols:
            if key == lv.KEY.LEFT:
                self.symbol_picker.cursor_left()
            elif key == lv.KEY.RIGHT:
                self.symbol_picker.cursor_right()
            elif key == lv.KEY.UP:
                self.symbol_picker.cursor_up()
            elif key == lv.KEY.DOWN:
                self.symbol_picker.cursor_down()
        else:
            self.t9.on_key(key)
            self.synchronize_with_t9()
