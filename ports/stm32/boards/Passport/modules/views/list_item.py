# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# list_item.py - Render a list item string, and an icon to indicate if that item is selected


import lvgl as lv
from views import Label, Icon
from styles import Stylize
from styles.colors import FOCUSED_LIST_ITEM_BG, NORMAL_TEXT, FOCUSED_LIST_ITEM_TEXT, NORMAL_TEXT
from views import View
from constants import MENU_ITEM_CORNER_RADIUS
from utils import derive_icon


class ListItem(View):
    def __init__(self, label='', is_selected=False, icon='ICON_SMALL_CHECKMARK', center=False):
        from utils import derive_icon

        super().__init__(flex_flow=lv.FLEX_FLOW.ROW)
        self.icon = derive_icon(icon)
        self.label = label
        self.is_selected = is_selected
        self.center = center

        # Default style
        with Stylize(self) as default:
            default.bg_transparent()
            default.text_color(NORMAL_TEXT)
            default.pad(top=8, right=8, bottom=8, left=8)
            default.flex_align(cross=lv.FLEX_ALIGN.CENTER)
            default.img_recolor(NORMAL_TEXT)
            default.radius(MENU_ITEM_CORNER_RADIUS)

        self.set_width(lv.pct(100))
        self.set_height(lv.SIZE.CONTENT)

        # Focus style
        with Stylize(self, selector=lv.STATE.FOCUS_KEY) as focus:
            focus.text_color(FOCUSED_LIST_ITEM_TEXT)
            focus.bg_color(FOCUSED_LIST_ITEM_BG)
            focus.img_recolor(FOCUSED_LIST_ITEM_TEXT)

        self.update_selected()

        # Label
        self.label_view = Label(text=self.label)
        with Stylize(self.label_view) as default:
            default.flex_fill()
            if self.center:
                default.text_align(lv.TEXT_ALIGN.CENTER)

        self.label_view.set_height(lv.SIZE.CONTENT)
        self.label_view.set_width(lv.pct(100))

        # Make the parent/child relationships
        self.add_child(self.label_view)

    def update_selected(self):
        if self.center:
            return

        if self.is_mounted():
            if self.icon_view is not None:
                self.icon_view.unmount()
                del self.children[0]

        if self.icon is not None:
            if self.is_selected:
                # Add the icon
                self.icon_view = Icon(icon=self.icon)
            else:
                # Add an empty view
                self.icon_view = View()

            self.icon_view.set_size(self.icon.header.w, self.icon.header.h)
            self.insert_child(0, self.icon_view)
        else:
            self.icon_view = None

        if self.is_mounted() and self.icon_view is not None:
            self.icon_view.mount(self.lvgl_root)
            self.icon_view.lvgl_root.move_to_index(0)

    def set_selected(self, is_selected):
        self.is_selected = is_selected
        self.update_selected()
