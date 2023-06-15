# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# file_item.py - Render a file item string, and an icon to indicate if that item is selected


import lvgl as lv
from views import Label, Icon
from styles import Stylize
from styles.colors import FOCUSED_LIST_ITEM_BG, FOCUSED_LIST_ITEM_TEXT, NORMAL_TEXT
from views import View
from constants import MENU_ITEM_CORNER_RADIUS


class FileItem(View):
    def __init__(self, filename='', is_folder=False):

        super().__init__(flex_flow=lv.FLEX_FLOW.ROW)
        self.filename = filename
        self.is_folder = is_folder

        # Default style
        with Stylize(self) as default:
            default.bg_transparent()
            default.text_color(NORMAL_TEXT)
            default.pad(top=10, right=0, bottom=10, left=10)
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

        # Icon
        self.icon_view = Icon(icon='ICON_FOLDER' if self.is_folder else 'ICON_FILE')

        # Filename
        self.filename_view = Label(text=self.filename)
        with Stylize(self.filename_view) as default:
            default.flex_fill()

        self.filename_view.set_height(lv.SIZE.CONTENT)

        # Make the parent/child relationships
        self.set_children([self.icon_view, self.filename_view])
