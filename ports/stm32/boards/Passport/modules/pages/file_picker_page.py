# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# file_picker_page.py - View to render a title and a list of files/folders.


import lvgl as lv
import microns
from styles.colors import TEXT_GREY
from styles import Stylize
from pages import Page
from views import FileItem, View
from micropython import const
import passport

MAX_FILE_DISPLAY = const(15) if passport.IS_COLOR else const(10)


class FilePickerPage(Page):
    def __init__(self,
                 files=[],
                 card_header=None,
                 statusbar=None,):
        from math import ceil

        super().__init__(card_header=card_header,
                         statusbar=statusbar,
                         flex_flow=lv.FLEX_FLOW.COLUMN,
                         left_micron=microns.Back,
                         right_micron=microns.Checkmark)

        self.files = files
        self.num_pages = ceil(len(files) / MAX_FILE_DISPLAY)
        self.page_idx = 0
        self.prev_card_descs = None
        self.prev_card_idx = None

        with Stylize(self) as default:
            default.flex_fill()
            default.flex_align(main=lv.FLEX_ALIGN.CENTER, cross=lv.FLEX_ALIGN.CENTER, track=lv.FLEX_ALIGN.CENTER)
            default.pad_row(0)

        # Set non-style props
        self.set_width(lv.pct(100))
        self.set_no_scroll()

        # Add a scroll container for the list items, but disable scrollbars until attached
        self.scroll_container = View(flex_flow=lv.FLEX_FLOW.COLUMN)
        self.scroll_container.set_no_scroll()
        self.scroll_container.set_width(lv.pct(100))

        with Stylize(self.scroll_container) as default:
            default.flex_fill()
            default.pad_row(0)

        # Adjust scrollbar position # TODO: adjust this in update()
        with Stylize(self.scroll_container, selector=lv.PART.SCROLLBAR) as scrollbar:
            scrollbar.pad(right=0)

        self.update()

    # async def display(self, auto_close_timeout=None):
    #     from pages import ErrorPage

    #     if len(self.files) > MAX_FILE_DISPLAY:
    #         await ErrorPage(text="Unable to display all files. Displaying the first "
    #                         "{} files alphabetically.".format(MAX_FILE_DISPLAY)).show()

    #     await super().display()

    def update(self):
        import common

        if self.is_mounted():
            self.scroll_container.unmount_children()
            self.scroll_container.set_children([])
            lv.gridnav_remove(self.scroll_container.lvgl_root)
            # lv.group_remove_obj(self.scroll_container.lvgl_root)
            self.unmount_children()
            self.set_children([])
            self.scroll_container.set_no_scroll()

        # add back option if there's a previous page
        if self.page_idx != 0:
            self.scroll_container.add_child(
                FileItem(filename='Previous', custom_icon=lv.ICON_BACK))

        # Add the file items to the scroll container
        range_start = self.page_idx * MAX_FILE_DISPLAY
        range_end = range_start + min(MAX_FILE_DISPLAY, (len(self.files) - range_start))
        for index in range(range_start, range_end):
            filename, _full_path, is_folder = self.files[index]
            self.scroll_container.add_child(
                FileItem(filename=filename, is_folder=is_folder))

        # add forward option if there are more pages:
        if self.page_idx < self.num_pages - 1:
            self.scroll_container.add_child(
                FileItem(filename='More', custom_icon=lv.ICON_FORWARD))

        self.add_child(self.scroll_container)

        if self.is_mounted():
            self.mount_children()
            self.scroll_container.set_scroll_dir(lv.DIR.VER)
            lv.gridnav_add(self.scroll_container.lvgl_root, lv.GRIDNAV_CTRL.NONE)
            # IMPORTANT: Add this to the group AFTER setting up gridnav
            # self.group.add_obj(self.scroll_container.lvgl_root)

        common.ui.set_micron_bar_active_idx(self.page_idx)

    def attach(self, group):
        from utils import add_page_dots

        super().attach(group)

        # Ensure scrollbars are enabled again
        self.scroll_container.set_scroll_dir(lv.DIR.VER)

        # Setup gridnav for the layout
        lv.gridnav_add(self.scroll_container.lvgl_root, lv.GRIDNAV_CTRL.NONE)
        group.add_obj(self.scroll_container.lvgl_root)  # IMPORTANT: Add this to the group AFTER setting up gridnav

        # Add pages dots if necessary
        add_page_dots(self, self.num_pages)

    def detach(self):
        from utils import remove_page_dots

        lv.group_remove_obj(self.scroll_container.lvgl_root)

        remove_page_dots(self)

        # Hide scrollbars during transitions
        self.scroll_container.set_no_scroll()
        super().detach()

    def get_selected_option_index_by_value(self, value):
        for index in range(len(self.options)):
            entry = self.options[index]
            if entry.get('value') == value:
                return index

        return 0

    def get_focused_item_index(self):
        if self.is_mounted():
            focused_item = lv.gridnav_get_focused(self.scroll_container.lvgl_root)

            # Look through the children to find what index the selected one is at
            for index in range(len(self.scroll_container.children)):
                item = self.scroll_container.children[index]
                if item.lvgl_root == focused_item:
                    return index

            # Should never happen
            assert(False)
            return None

    def left_action(self, is_pressed):
        if not is_pressed:
            self.set_result(None)

    def right_action(self, is_pressed):
        if not is_pressed:
            try:
                selected_option_idx = self.get_focused_item_index()

                # TODO: add back/forward page controls
                # Go back a page
                if self.page_idx != 0 and selected_option_idx == 0:
                    self.page_idx -= 1
                    self.update()
                    return

                # Go forward a page
                if self.page_idx < self.num_pages - 1 \
                        and selected_option_idx == len(self.scroll_container.children) - 1:
                    self.page_idx += 1
                    self.update()
                    return

                selected_file = self.files[selected_option_idx]
                # print('Selected file: {}'.format(selected_file))
                self.set_result(selected_file)
            except Exception as e:
                assert(False, '{}'.format(e))
