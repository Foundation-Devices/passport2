# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# color_picker.py -RGB color picker for RGB565 colors

import lvgl as lv
from micropython import const
from styles import Stylize
from styles.colors import BLACK, BLUE, GREEN, LIGHT_GREY, RED, WHITE
from styles.local_style import LocalStyle
from views import View, Label, Slider

_SLIDER_HEIGHT = const(16)
_SLIDER_WIDTH = const(220)


class ColorPicker(View):
    def __init__(self, flex_flow=lv.FLEX_FLOW.COLUMN, initial_color=0xBF755F):
        super().__init__(flex_flow=flex_flow)
        with Stylize(self) as default:
            default.bg_color(WHITE)
            default.pad_all(8)
            default.pad_row(18)
        self.set_width(lv.pct(100))
        self.initial_color = initial_color

        self.swatch = View()
        with Stylize(self.swatch) as default:
            default.flex_fill()
        self.swatch.set_width(lv.pct(100))
        self.swatch.clear_flag(lv.obj.FLAG.CLICK_FOCUSABLE)

        self.color_label = Label()
        with Stylize(self.color_label) as default:
            default.text_color(BLACK)
            default.text_align(lv.TEXT_ALIGN.CENTER)
        self.color_label.set_width(lv.pct(100))
        self.color_label.clear_flag(lv.obj.FLAG.CLICK_FOCUSABLE)

        self.red = ((self.initial_color & 0xFF0000) >> 16) >> 3
        self.green = ((self.initial_color & 0x00FF00) >> 8) >> 2
        self.blue = (self.initial_color & 0x0000FF) >> 3

        self.red_slider = Slider(
            range=(0, 31),
            initial_value=self.red,
            knob_color=RED, track_color=RED.color_darken(lv.OPA._40),
            on_change=self.on_red_change)
        with Stylize(self.red_slider) as default:
            default.flex_align(main=lv.FLEX_ALIGN.CENTER, cross=lv.FLEX_ALIGN.CENTER)
            self.red_slider.set_height(_SLIDER_HEIGHT)
            self.red_slider.set_width(_SLIDER_WIDTH)

        self.green_slider = Slider(
            range=(0, 63),
            initial_value=self.green,
            knob_color=GREEN, track_color=GREEN.color_darken(lv.OPA._40),
            on_change=self.on_green_change)
        with Stylize(self.green_slider) as default:
            default.flex_align(main=lv.FLEX_ALIGN.CENTER, cross=lv.FLEX_ALIGN.CENTER)
            self.green_slider.set_height(_SLIDER_HEIGHT)
            self.green_slider.set_width(_SLIDER_WIDTH)

        self.blue_slider = Slider(
            range=(0, 31),
            initial_value=self.blue,
            knob_color=BLUE, track_color=BLUE.color_darken(lv.OPA._40),
            on_change=self.on_blue_change)
        with Stylize(self.blue_slider) as default:
            default.flex_align(main=lv.FLEX_ALIGN.CENTER, cross=lv.FLEX_ALIGN.CENTER)
            self.blue_slider.set_height(_SLIDER_HEIGHT)
            self.blue_slider.set_width(_SLIDER_WIDTH)
        self.set_children([self.swatch, self.color_label, self.red_slider, self.green_slider, self.blue_slider])

    def attach(self, group):
        super().attach(group)
        self.red_slider.attach(group)
        self.green_slider.attach(group)
        self.blue_slider.attach(group)
        lv.gridnav_add(self.lvgl_root, lv.GRIDNAV_CTRL.NONE)
        group.add_obj(self.lvgl_root)  # IMPORTANT: Add this to the group AFTER setting up gridnav

        self.update_swatch()

    def detach(self):
        lv.group_remove_obj(self.lvgl_root)
        super().detach()

    def on_red_change(self, red):
        self.red = red
        self.update_swatch()

    def on_green_change(self, green):
        self.green = green
        self.update_swatch()

    def on_blue_change(self, blue):
        self.blue = blue
        self.update_swatch()

    def update_swatch(self):
        red = self.red << 3
        green = self.green << 2
        blue = self.blue << 3
        color_hex = '##{:02x}{:02x}{:02x}'.format(red, green, blue)
        print('color_hex={}'.format(color_hex))
        self.color_label.set_text(color_hex)
        with LocalStyle(self.swatch) as default:
            default.bg_color(lv.color_make(red, green, blue))
