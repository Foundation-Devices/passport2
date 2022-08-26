# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# file_picker_page.py - View to render a title and a list of files/folders.


import lvgl as lv
import microns
from styles.colors import TEXT_GREY
from styles import Stylize
from pages import Page
from views import FileItem, View


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

        # Adjust scrollbar position
        with Stylize(self.scroll_container, selector=lv.PART.SCROLLBAR) as scrollbar:
            scrollbar.pad(right=0)

        # Add the file items to the scroll container
        for index in range(len(self.files)):
            filename, _full_path, is_folder = self.files[index]
            self.scroll_container.add_child(
                FileItem(filename=filename, is_folder=is_folder))

        self.add_child(self.scroll_container)

    def attach(self, group):
        super().attach(group)

        # Ensure scrollbars are enabled again
        self.scroll_container.set_scroll_dir(lv.DIR.VER)

        # Setup gridnav for the layout
        gridnav_options = lv.GRIDNAV_CTRL.ROLLOVER | lv.GRIDNAV_CTRL.IGNORE_HORIZONTAL_KEYS
        lv.gridnav_add(self.scroll_container.lvgl_root, gridnav_options)
        group.add_obj(self.scroll_container.lvgl_root)  # IMPORTANT: Add this to the group AFTER setting up gridnav

    def detach(self):
        lv.group_remove_obj(self.scroll_container.lvgl_root)

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
                selected_file = self.files[selected_option_idx]
                # print('Selected file: {}'.format(selected_file))
                self.set_result(selected_file)
            except Exception as e:
                assert(False, '{}'.format(e))
