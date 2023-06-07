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

# Returns a tuple where the first value is the string to show in the list and the second value is
# whether to show the default icon or the alt icon.
# NOTE: Doesn't support showing arbitrary icons at this time.
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

        # Add a scroll container for the list items, but disable scrollbars until attached
        # self.scroll_container = View(flex_flow=lv.FLEX_FLOW.COLUMN)
        # self.scroll_container.set_no_scroll()
        # self.scroll_container.set_width(lv.pct(100))

        # with Stylize(self.scroll_container) as default:
        #     default.flex_fill()
        #     default.pad_row(0)

        # # Adjust scrollbar position
        # with Stylize(self.scroll_container, selector=lv.PART.SCROLLBAR) as scrollbar:
        #     scrollbar.pad(right=0)

        # Add the file items to the scroll container
        # num_files = min(MAX_FILE_DISPLAY, len(self.files))
        # for index in range(num_files):
        #     filename, _full_path, is_folder = self.files[index]
        #     self.scroll_container.add_child(
        #         FileItem(filename=filename, is_folder=is_folder))


    # async def display(self, auto_close_timeout=None):
    #     from pages import ErrorPage

    #     if len(self.files) > MAX_FILE_DISPLAY:
    #         await ErrorPage(text="Unable to display all files. Displaying the first "
    #                         "{} files alphabetically.".format(MAX_FILE_DISPLAY)).show()

    #     await super().display()

    def attach(self, group):
        super().attach(group)
        group.add_obj(self.table.lvgl_root)  # IMPORTANT: Add this to the group AFTER setting up gridnav

    #     # Ensure scrollbars are enabled again
    #     # self.scroll_container.set_scroll_dir(lv.DIR.VER)


    #     # Setup gridnav for the layout
    #     # lv.gridnav_add(self.scroll_container.lvgl_root, lv.GRIDNAV_CTRL.NONE)
    #     # group.add_obj(self.scroll_container.lvgl_root)  # IMPORTANT: Add this to the group AFTER setting up gridnav

    def detach(self):
        self.table.set_no_scroll()
        super().detach()

    #     # Hide scrollbars during transitions
    #     self.scroll_container.set_no_scroll()
    #     super().detach()

    # def get_selected_option_index_by_value(self, value):
    #     for index in range(len(self.options)):
    #         entry = self.options[index]
    #         if entry.get('value') == value:
    #             return index

    #     return 0

    # def get_focused_item_index(self):
        # if self.is_mounted():
        #     focused_item = lv.gridnav_get_focused(self.scroll_container.lvgl_root)

        #     # Look through the children to find what index the selected one is at
        #     for index in range(len(self.scroll_container.children)):
        #         item = self.scroll_container.children[index]
        #         if item.lvgl_root == focused_item:
        #             return index

        #     # Should never happen
        #     assert(False)
        #     return None

    def left_action(self, is_pressed):
        if not is_pressed:
            self.set_result(None)

    def right_action(self, is_pressed):
        print('Right Action!')
        if not is_pressed:
            try:
                selected_idx = self.table.get_selected_row()
                print('selected: {}'.format(selected_idx))
                selected_file = self.files[selected_idx]
                print('Selected file: {}'.format(selected_file))
                self.set_result(selected_file)
            except Exception as e:
                print("Exception: {}".format(e))
                assert(False, '{}'.format(e))