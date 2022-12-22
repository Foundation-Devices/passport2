# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# text_input.py - Single line text input component


import lvgl as lv
from styles.style import Stylize
from views import View
from utils import InputMode
from views import Icon, TextArea
from styles.colors import TEXT_INPUT_BG, TEXT_INPUT_ICON
from constants import MENU_ITEM_CORNER_RADIUS

_SIDE_WIDTH = const(18)


class TextInput(View):
    def __init__(self, text='', input_mode=InputMode.UPPER_ALPHA, one_line=True):
        super().__init__(flex_flow=lv.FLEX_FLOW.ROW)
        self.text = text
        self.input_mode = input_mode
        self.one_line = one_line

        self.set_size(lv.pct(100), 35)

        with Stylize(self) as default:
            default.radius(MENU_ITEM_CORNER_RADIUS)
            default.bg_color(TEXT_INPUT_BG)
            default.no_pad()
            default.pad_col(2)
            default.flex_align(cross=lv.FLEX_ALIGN.CENTER)
            default.clip_corner(True)

        self.mode_view = View(lv.FLEX_FLOW.COLUMN)
        self.mode_view.set_size(_SIDE_WIDTH, lv.pct(100))
        with Stylize(self.mode_view) as default:
            default.pad(left=2)
            default.flex_align(main=lv.FLEX_ALIGN.CENTER, cross=lv.FLEX_ALIGN.CENTER, track=lv.FLEX_ALIGN.CENTER)

        self.mode_icon = Icon(InputMode.get_icon(self.input_mode), color=TEXT_INPUT_ICON)
        self.mode_view.add_child(self.mode_icon)

        self.filler = View(flex_flow=lv.FLEX_FLOW.COLUMN)
        self.filler.set_width(_SIDE_WIDTH)
        self.filler.set_height(lv.pct(100))

        self.text_area = TextArea(text=self.text, one_line=self.one_line)

        if not self.one_line:
            # TODO: Decide what height to make this for multi-line input
            self.text_area.set_height(80)

        with Stylize(self.text_area) as default:
            default.flex_fill()
            default.align(lv.ALIGN.CENTER)
            # default.bg_color(GREEN, opa=128)

        self.set_children([self.mode_view, self.text_area, self.filler])

    def cursor_left(self):
        self.text_area.cursor_left()

    def cursor_right(self):
        self.text_area.cursor_right()

    def cursor_up(self):
        self.text_area.cursor_up()

    def cursor_down(self):
        self.text_area.cursor_down()

    def set_cursor_pos(self, pos):
        self.text_area.set_cursor_pos(pos)

    def add_char(self, char):
        self.text_area.add_char(char)

    def del_char(self):
        self.text_area.del_char()

    def get_text(self):
        if self.is_mounted():
            return self.text_area.lvgl_root.get_text()
        else:
            return ''

    def set_text(self, text):
        self.text = text
        if self.is_mounted():
            self.text_area.lvgl_root.set_text(text)

    def set_mode(self, mode):
        self.input_mode = mode
        self.mode_icon.set_icon(InputMode.get_icon(self.input_mode))
