# SPDX-FileCopyrightText: 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# statusbar.py - Top status bar that shows a title and some icons


import lvgl as lv
from views import View, Icon, BoldLabel, BatteryIndicator
from styles import Stylize
from styles.colors import WHITE
from constants import STATUS_BAR_HEIGHT


class StatusBar(View):
    def __init__(self, title='', icon=None, fg_color=WHITE):
        super().__init__(flex_flow=lv.FLEX_FLOW.ROW)
        self.secs = 0
        self.title = title
        self.icon = icon
        self.fg_color = fg_color

        self.title_view = None
        self.icon_view = None

        with Stylize(self) as default:
            default.pad(top=0, bottom=0, left=10, right=10)
            default.flex_align(main=lv.FLEX_ALIGN.START, cross=lv.FLEX_ALIGN.CENTER, track=lv.FLEX_ALIGN.CENTER)

        self.set_size(lv.pct(100), STATUS_BAR_HEIGHT)
        self.set_pos(0, 0)
        self.set_no_scroll()

        self.update_icon()

        self.update_title()

        self.battery = BatteryIndicator()

        self.add_child(self.battery)

    def update_icon(self):
        if self.is_mounted():
            self.icon_view.unmount()
            del self.children[0]

        if self.icon is None:
            self.icon_view = Icon(icon=lv.ICON_SETTINGS, opa=0)  # Transparent placeholder
        else:
            self.icon_view = Icon(icon=self.icon, color=self.fg_color)
        self.insert_child(0, self.icon_view)

        if self.is_mounted():
            self.icon_view.mount(self.lvgl_root)
            self.icon_view.lvgl_root.move_to_index(0)

    def update_title(self):
        if self.is_mounted():
            self.title_view.unmount()
            del self.children[1]

        self.title_view = BoldLabel(text=self.title, color=self.fg_color, center=True)
        with Stylize(self.title_view) as default:
            default.flex_fill()
        self.insert_child(1, self.title_view)

        if self.is_mounted():
            self.title_view.mount(self.lvgl_root)
            self.title_view.lvgl_root.move_to_index(1)

    def set_battery_level(self, battery_level):
        self.battery.set_percent(battery_level)

    def set_is_charging(self, is_charging):
        self.battery.set_is_charging(is_charging)

    def set_title(self, title):
        self.title = title
        self.update_title()

    def set_icon(self, icon):
        self.icon = icon
        self.update_icon()

    def set_fg_color(self, fg_color):
        self.fg_color = fg_color
        self.battery.set_outline_color(self.fg_color)
        self.update_title()
        self.update_icon()
