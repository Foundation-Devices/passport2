# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# battery_indicator.py - Render the battery icon with a fill corresponding to the current state of charge


import lvgl as lv
from micropython import const
from views import View, Icon
from styles.colors import BATTERY_FILL_COLOR, WHITE, TEXT_GREY
from styles import Stylize, LocalStyle

_LEFT_MARGIN = const(2)
_TOP_MARGIN = const(5)
_FILL_HEIGHT = const(9)
_FILL_MAX_WIDTH = const(16)


class BatteryIndicator(View):
    def __init__(self, outline_color=WHITE):
        super().__init__()
        self.percent = 100
        self.is_charging = False
        self.outline_color = outline_color

        self.icon = Icon(lv.ICON_BATTERY, color=WHITE)
        self.set_size(lv.SIZE.CONTENT, lv.SIZE.CONTENT)
        with Stylize(self.icon) as default:
            default.align(lv.ALIGN.CENTER)

        self.bg_fill = View()
        self.bg_fill.set_size(_FILL_MAX_WIDTH, _FILL_HEIGHT)
        self.bg_fill.set_pos(_LEFT_MARGIN, _TOP_MARGIN)
        with Stylize(self.bg_fill) as default:
            default.bg_color(TEXT_GREY)

        self.fill = View()
        self.fill.set_height(_FILL_HEIGHT)
        self.fill.set_pos(_LEFT_MARGIN, _TOP_MARGIN)
        with Stylize(self.fill) as default:
            default.bg_color(BATTERY_FILL_COLOR)

        self.update_fill()

        self.set_children([self.bg_fill, self.fill, self.icon])

    def update_fill(self):
        self.fill.set_width((self.percent * _FILL_MAX_WIDTH) // 100)

    def update_icon(self):
        with LocalStyle(self.icon) as style:
            style.img_recolor(self.outline_color)

    def set_percent(self, percent):
        self.percent = percent
        self.update_fill()

    def set_is_charging(self, is_charging):
        self.is_charging = is_charging
        if self.is_charging:
            self.icon.set_icon(lv.ICON_BATTERY_CHARGING)
        else:
            self.icon.set_icon(lv.ICON_BATTERY)

    def set_outline_color(self, outline_color):
        self.outline_color = outline_color
        self.update_icon()
