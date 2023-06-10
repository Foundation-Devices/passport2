# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# file_picker_page.py - View to render a title and a list of files/folders.


import lvgl as lv
import microns
from styles.colors import TEXT_GREY, WHITE, FD_BLUE
from styles import Stylize
from pages import Page
from views import Table
from micropython import const
from constants import MENU_ITEM_CORNER_RADIUS
import passport

MAX_FILE_DISPLAY = const(15) if passport.IS_COLOR else const(10)


def get_file_info(item):
    (filename, _full_path, is_folder) = item
    return (filename, is_folder)


class FilePickerPage(Page):
    def __init__(self,
                 files=[],
                 card_header=None,
                 statusbar=None,):
        super().__init__(card_header=card_header,
                         statusbar=statusbar,
                         flex_flow=lv.FLEX_FLOW.COLUMN,
                         left_micron=microns.Back,
                         right_micron=microns.Checkmark)

        self.files = files

        with Stylize(self) as default:
            default.flex_fill()
            default.flex_align(main=lv.FLEX_ALIGN.CENTER, cross=lv.FLEX_ALIGN.CENTER, track=lv.FLEX_ALIGN.CENTER)
            default.pad_row(0)
            default.bg_color(WHITE)

        # Set non-style props
        self.set_width(lv.pct(100))
        self.set_no_scroll()

        self.table = Table(items=self.files, get_cell_info=get_file_info)
        self.table.set_width(lv.pct(100))
        self.table.set_height(lv.pct(100))
        self.table.set_scroll_dir(lv.DIR.VER)

        with Stylize(self.table) as default:
            default.flex_fill()
            default.pad_row(0)

        # Adjust scrollbar position
        with Stylize(self.table, selector=lv.PART.SCROLLBAR) as scrollbar:
            scrollbar.pad(right=0)

        with Stylize(self.table, lv.PART.MAIN) as default:
            default.bg_color(WHITE)
            default.radius(4)
            default.border_width(0)

        with Stylize(self.table, lv.PART.ITEMS) as items:
            items.bg_color(WHITE)
            items.text_color(TEXT_GREY)
            items.border_width(0)
            items.radius(MENU_ITEM_CORNER_RADIUS)

        with Stylize(self.table, lv.PART.ITEMS | lv.STATE.FOCUS_KEY) as focused:
            focused.bg_color(FD_BLUE)

        self.add_child(self.table)

    def attach(self, group):
        super().attach(group)
        group.add_obj(self.table.lvgl_root)

    def detach(self):
        self.table.set_no_scroll()
        super().detach()

    def left_action(self, is_pressed):
        if not is_pressed:
            self.set_result(None)

    def right_action(self, is_pressed):
        if not is_pressed:
            try:
                selected_idx = self.table.get_selected_row()
                selected_file = self.files[selected_idx]
                self.set_result(selected_file)
            except Exception as e:
                print("Exception: {}".format(e))
                assert(False, '{}'.format(e))
