# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# menu_item.py - Component to render a single menu item (icon and label)


import lvgl as lv
from views import Label, Icon
from styles import Stylize
from styles.colors import FOCUSED_LIST_ITEM_TEXT, FOCUSED_LIST_ITEM_BG, NORMAL_TEXT
from constants import MENU_ITEM_CORNER_RADIUS
from views import View
from utils import derive_icon


class MenuItem(View):
    def __init__(self, icon='', label='', is_toggle=False, value=False, desc=None, context=None):
        from views import Switch

        super().__init__(flex_flow=lv.FLEX_FLOW.ROW)
        self.icon = derive_icon(icon)
        self.label = label
        self.is_toggle = is_toggle
        self.value = value
        self.desc = desc
        self.context = context

        # Default style
        with Stylize(self) as default:
            default.bg_transparent()
            default.text_color(NORMAL_TEXT)
            right_pad = 8 if self.is_toggle else 0
            default.pad(top=10, right=right_pad, bottom=10, left=10)
            default.flex_align(track=lv.FLEX_ALIGN.CENTER, cross=lv.FLEX_ALIGN.CENTER)
            default.img_recolor(NORMAL_TEXT)

        self.set_width(lv.pct(100))
        self.set_height(lv.SIZE.CONTENT)

        # Focus style
        with Stylize(self, selector=lv.STATE.FOCUS_KEY) as focus:
            focus.text_color(FOCUSED_LIST_ITEM_TEXT)
            focus.bg_color(FOCUSED_LIST_ITEM_BG)
            focus.radius(MENU_ITEM_CORNER_RADIUS)
            focus.img_recolor(FOCUSED_LIST_ITEM_TEXT)

        # Icon
        self.icon_view = Icon(icon=self.icon)
        self.icon_view.set_size(21, lv.SIZE.CONTENT)
        self.add_child(self.icon_view)

        # Label
        self.label_view = Label(text=self.label)
        with Stylize(self.label_view) as default:
            default.flex_fill()
        self.label_view.set_height(lv.SIZE.CONTENT)
        self.add_child(self.label_view)

        # Add the toggle, if present
        if self.is_toggle:
            # Value can be a simple value or a callable, which allows its value to be updated
            value = self.value
            if callable(value):
                value = value(self.context)
            self.switch_view = Switch(value=value)
            self.switch_view.set_size(46, 24)
            self.add_child(self.switch_view)
