# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# menu_item.py - Component to render a single menu item (icon and label)


import lvgl as lv
from views import Label, Icon
from styles import Stylize
from styles.colors import FD_BLUE, WHITE, DARK_GREY
from constants import MENU_ITEM_CORNER_RADIUS
from views import View


class MenuItem(View):
    def __init__(self, icon='', label='', desc=None):

        super().__init__(flex_flow=lv.FLEX_FLOW.ROW)
        self.icon = icon
        self.label = label
        self.desc = desc

        # Default style
        with Stylize(self) as default:
            default.bg_transparent()
            default.text_color(DARK_GREY)
            default.pad(top=10, right=0, bottom=10, left=10)
            default.flex_align(cross=lv.FLEX_ALIGN.CENTER)
            default.img_recolor(DARK_GREY)

        self.set_width(lv.pct(100))
        self.set_height(40)

        # Focus style
        with Stylize(self, selector=lv.STATE.FOCUS_KEY) as focus:
            focus.text_color(WHITE)
            focus.bg_color(FD_BLUE)
            focus.radius(MENU_ITEM_CORNER_RADIUS)
            focus.img_recolor(WHITE)

        # Icon
        self.icon_view = Icon(icon=self.icon)
        self.icon_view.set_width(20)
        self.icon_view.set_height(lv.SIZE.CONTENT)

        # Label
        self.label_view = Label(text=self.label)
        with Stylize(self.label_view) as default:
            default.flex_fill()

        self.label_view.set_height(lv.SIZE.CONTENT)

        # Make the parent/child relationships
        self.set_children([self.icon_view, self.label_view])
