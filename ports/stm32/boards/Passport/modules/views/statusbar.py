# SPDX-FileCopyrightText: 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# statusbar.py - Top status bar that shows a title and some icons


import lvgl as lv
from views import View, Icon, BoldLabel, BatteryIndicator
from styles import Stylize
from styles.colors import WHITE, BLACK
from constants import STATUSBAR_HEIGHT
import passport


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
            # if not passport.IS_COLOR:
            # default.bg_color(BLACK)

            default.pad(top=0, bottom=0, left=10, right=10)
            default.pad_col(2)
            default.flex_align(main=lv.FLEX_ALIGN.START, cross=lv.FLEX_ALIGN.CENTER, track=lv.FLEX_ALIGN.CENTER)

        self.set_size(lv.pct(100), STATUSBAR_HEIGHT)
        self.set_pos(0, 0)
        self.set_no_scroll()

        self.update_icon()

        self.update_title()

        self.battery = BatteryIndicator()
        if passport.IS_COLOR:
            self.add_child(self.battery)
        else:
            self.battery_container = View(flex_flow=None)
            self.battery_container.set_size(lv.SIZE.CONTENT, lv.SIZE.CONTENT)
            # self.battery_container.set_size(24, 24)
            with Stylize(self.battery_container) as default:
                default.bg_color(BLACK)
                default.pad(left=2, right=2)
                default.radius(4)
                default.align(lv.ALIGN.CENTER)

            self.battery_container.add_child(self.battery)
            self.add_child(self.battery_container)

    def update_icon(self):
        if self.is_mounted():
            self.icon_view.unmount()
            del self.children[0]

        if self.icon is None:
            icon_view = Icon(icon=lv.ICON_SETTINGS, opa=0)  # Transparent placeholder
        else:
            icon_view = Icon(icon=self.icon, color=self.fg_color)

        if passport.IS_COLOR:
            self.icon_view = icon_view
        else:
            self.icon_view = View(flex_flow=None)
            self.icon_view.set_size(lv.SIZE.CONTENT, lv.SIZE.CONTENT)
            with Stylize(self.icon_view) as default:
                default.bg_color(BLACK)
                default.pad_all(2)
                default.radius(4)
                default.align(lv.ALIGN.CENTER)

            self.icon_view.add_child(icon_view)
            self.add_child(self.icon_view)

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
        self.fg_color = WHITE
        self.battery.set_outline_color(self.fg_color)
        self.update_title()
        self.update_icon()
