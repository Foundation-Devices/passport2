# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# button.py - Basic button


import lvgl as lv
from views import View, Label
from styles import Stylize, FONT_NORMAL


class Button(View):
    def __init__(
            self, text='', text_color=None, bg_color=None, align=lv.TEXT_ALIGN.CENTER, font=FONT_NORMAL,
            on_clicked=None):
        super().__init__()
        self.text = text
        self.text_color = text_color
        self.bg_color = bg_color
        self.align = align
        self.font = font
        self.on_clicked = on_clicked

        self.label = Label(text=text, color=text_color)
        self.label.set_width(lv.pct(100))
        with Stylize(self.label) as default:
            default.font(self.font)
            default.text_align(self.align)
            if self.text_color is not None:
                default.text_color(self.text_color)

        with Stylize(self) as default:
            if self.bg_color is not None:
                default.bg_color(self.bg_color)

        self.set_children([self.label])

    # def set_text(self, text):
    #     self.text = text
    #     if self.is_mounted():
    #         self.lvgl_root.set_text(text)

    def create_lvgl_root(self, lvgl_parent):
        return lv.btn(lvgl_parent)

    def mount(self, lvgl_parent):
        super().mount(lvgl_parent)

        return self.lvgl_root

    def attach(self, group):
        super().attach(group)
        self.lvgl_root.add_event_cb(lambda _: self.on_clicked(), lv.EVENT.CLICKED, None)
