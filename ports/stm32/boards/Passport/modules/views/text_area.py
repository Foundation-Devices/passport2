# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# text_area.py - Wrapper around lvgl textarea


import lvgl as lv
from views import View
from styles import Stylize
from styles.colors import TEXT_INPUT_CURSOR, TEXT_INPUT_TEXT


class TextArea(View):
    def __init__(self, text='', one_line=False):
        super().__init__()
        self.text = text
        self.one_line = one_line

        self.set_no_scroll()
        self.set_width(lv.pct(50))
        with Stylize(self) as default:
            default.text_color(TEXT_INPUT_TEXT)
            default.bg_transparent()
            default.border_width(0)
            default.text_align(lv.TEXT_ALIGN.CENTER)

        with Stylize(self, selector=lv.PART.CURSOR) as cursor:
            cursor.border_color(TEXT_INPUT_CURSOR)
            cursor.border_width(2)
            cursor.border_side(lv.BORDER_SIDE.LEFT)
            cursor.anim_time(500)

    def mount(self, lvgl_parent):
        super().mount(lvgl_parent)

        self.lvgl_root.set_text(self.text)
        self.lvgl_root.set_one_line(self.one_line)

        return self.lvgl_root

    def create_lvgl_root(self, lvgl_parent):
        return lv.textarea(lvgl_parent)

    def cursor_left(self):
        if self.is_mounted():
            self.lvgl_root.cursor_left()

    def cursor_right(self):
        if self.is_mounted():
            self.lvgl_root.cursor_right()

    def cursor_up(self):
        if self.is_mounted():
            self.lvgl_root.cursor_up()

    def cursor_down(self):
        if self.is_mounted():
            self.lvgl_root.cursor_down()

    def set_cursor_pos(self, pos):
        if self.is_mounted():
            self.lvgl_root.set_cursor_pos(pos)

    def add_char(self, char):
        if self.is_mounted():
            self.lvgl_root.add_char(ord(char))

    def del_char(self):
        if self.is_mounted():
            self.lvgl_root.del_char()
