# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# pin_input.py - Single PIN input


import lvgl as lv
from styles import Stylize
from styles.colors import TEXT_GREY, TEXT_INPUT_BG, TEXT_INPUT_CURSOR, TEXT_INPUT_TEXT, TEXT_INPUT_CURSOR
from views import View
from utils import InputMode
from views import Label, Icon
from constants import MENU_ITEM_CORNER_RADIUS, MAX_PIN_LEN

_SIDE_WIDTH = const(18)


class PINInput(View):
    def __init__(self, pin='', input_mode=InputMode.UPPER_ALPHA):
        super().__init__()
        self.pin = pin
        self.input_mode = input_mode
        self.show_last_char = False
        self.timer = None

        self.set_size(lv.pct(100), 35)

        with Stylize(self) as default:
            default.radius(MENU_ITEM_CORNER_RADIUS)
            default.bg_color(TEXT_INPUT_BG)
            default.no_pad()
            default.pad_col(4)

        self.mode_view = View(lv.FLEX_FLOW.COLUMN)
        self.mode_view.set_size(_SIDE_WIDTH, lv.pct(100))
        with Stylize(self.mode_view) as default:
            default.pad(left=2)
            default.flex_align(main=lv.FLEX_ALIGN.CENTER, cross=lv.FLEX_ALIGN.CENTER, track=lv.FLEX_ALIGN.CENTER)

        self.mode_icon = Icon(InputMode.get_icon(self.input_mode), color=TEXT_GREY)
        self.mode_view.add_child(self.mode_icon)

        self.pin_container = View(flex_flow=lv.FLEX_FLOW.ROW)
        self.pin_container.set_size(lv.pct(80), 30)
        with Stylize(self.pin_container) as default:
            default.flex_align(main=lv.FLEX_ALIGN.CENTER, cross=lv.FLEX_ALIGN.CENTER, track=lv.FLEX_ALIGN.CENTER)
            default.align(lv.ALIGN.CENTER)
            default.pad_col(3)

        self.filler = View(flex_flow=lv.FLEX_FLOW.COLUMN)
        self.filler.set_width(_SIDE_WIDTH)
        self.filler.set_height(lv.pct(100))

        self.set_children([self.mode_view, self.pin_container, self.filler])

        self.update_pin()

    def update_pin(self):
        if self.is_mounted():
            self.pin_container.unmount_children()
            self.pin_container.set_children([])

        num_chars = len(self.pin)
        for i in range(num_chars):
            # ch = self.pin[i]
            # item = Label(text=ch, color=TEXT_GREY)
            if i == num_chars - 1 and self.show_last_char:
                ch = self.pin[i]
                item = Label(text=ch, color=TEXT_INPUT_TEXT)
            else:
                item = Icon(lv.ICON_PAGE_DOT, color=TEXT_INPUT_TEXT)
            self.pin_container.add_child(item)

        # Finally, draw a "cursor", which is always at the end
        cursor = Label(text='|', color=TEXT_INPUT_CURSOR)
        self.pin_container.add_child(cursor)

        if self.is_mounted():
            self.pin_container.mount_children()

    def add_char(self, char):
        if len(self.pin) < MAX_PIN_LEN:
            self.pin += char
            self.show_last_char = True
            if self.timer is not None:
                self.timer._del()
                self.timer = None
            self.timer = lv.timer_create(self.on_timer, 1000, None)
            self.update_pin()

    def del_char(self):
        if len(self.pin) > 0:
            self.pin = self.pin[0:-1]
            self.show_last_char = False
            self.update_pin()

    def on_timer(self, t):
        self.timer._del()
        self.timer = None
        self.show_last_char = False
        self.update_pin()

    def set_pin(self, pin):
        # This makes the character visible when a new character is added,
        # or when the latest character is still being modified
        if len(pin) > len(self.pin) or (len(pin) > 0 and len(pin) == len(self.pin) and pin[-1] != self.pin[-1]):
            self.show_last_char = True
            if self.timer is not None:
                self.timer._del()
                self.timer = None
            self.timer = lv.timer_create(self.on_timer, 1000, None)

        self.pin = pin
        self.update_pin()

    def get_pin(self):
        if self.is_mounted():
            return self.pin
        else:
            return ''

    def set_mode(self, mode):
        self.input_mode = mode
        self.mode_icon.set_icon(InputMode.get_icon(self.input_mode))
