# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# menu_page.py - View to render a list of menu items


import lvgl as lv
from styles import Stylize
from pages import Page
from views import MenuItem
import common
import microns


class MenuPage(Page):
    def __init__(self,
                 item_descs=[],
                 focus_idx=0,
                 is_top_level=None,
                 card_header=None,
                 statusbar=None,
                 left_micron=None,
                 right_micron=None):
        super().__init__(card_header=card_header,
                         statusbar=statusbar,
                         left_micron=left_micron,
                         right_micron=right_micron,
                         flex_flow=lv.FLEX_FLOW.COLUMN)
        self.item_descs = item_descs
        self.visible_items = []

        self.focus_idx = focus_idx
        self.is_top_level = is_top_level

        with Stylize(self) as default:
            default.flex_fill()
            default.pad_row(-4)

        # Adjust scrollbar position
        with Stylize(self, selector=lv.PART.SCROLLBAR) as scrollbar:
            scrollbar.pad(right=0)

        # Set non-style props
        self.set_width(lv.pct(100))

        # Disable scrollbars until attached
        self.set_no_scroll()

    def mount(self, lvgl_parent):
        # Filter to ones that are visible before calling base class since the base class
        # is where children are connected to the parent.
        # This is re-evaluated each time the view is mounted.
        if len(self.visible_items) > 0:
            self.visible_items = []

        for index in range(len(self.item_descs)):
            item_desc = self.item_descs[index]
            item = MenuItem(
                icon=item_desc.get('icon'),
                label=item_desc.get('label'),
                desc=item_desc)
            is_visible = item_desc.get('is_visible')
            if is_visible is None or (callable(is_visible) and is_visible()):
                self.visible_items.append(item)
        self.set_children(self.visible_items)

        super().mount(lvgl_parent)

        if self.is_top_level is not None:
            common.ui.set_is_top_level(self.is_top_level)

    def unmount(self):
        super().unmount()
        if self.is_top_level is not None:
            common.ui.set_is_top_level(False)

    def attach(self, group):
        super().attach(group)

        # Attach child views
        for item in self.visible_items:
            item.attach(group)

        # Ensure scrollbars are enabled again
        self.set_scroll_dir(lv.DIR.VER)

        # Setup gridnav for the layout
        num_items = len(self.visible_items)
        if (self.focus_idx >= num_items):
            self.focus_idx = num_items - 1

        initial_focus = self.visible_items[self.focus_idx].get_lvgl_root()
        lv.gridnav_add(self.lvgl_root, lv.GRIDNAV_CTRL.ROLLOVER)
        group.add_obj(self.lvgl_root)  # IMPORTANT: Add this to the group AFTER setting up gridnav
        lv.gridnav_set_focused(self.lvgl_root, initial_focus, False)

        common.ui.set_left_micron(microns.Shutdown if common.ui.is_top_level() else microns.Back)

    def detach(self):
        # Update this so that we can restore to the same index later if this MenuPage is
        # remounted/reattached (e.g., when the power button is pressed, then shutdown is canceled).
        self.focus_idx, _ = self.get_focused_item()

        lv.group_remove_obj(self.lvgl_root)

        # Hide scrollbars during transitions
        self.set_no_scroll()

        for item in self.visible_items:
            item.detach()
        super().detach()

    def get_focused_item(self):
        if self.is_mounted():
            focused_item = lv.gridnav_get_focused(self.lvgl_root)

            for index in range(len(self.visible_items)):
                item = self.visible_items[index]
                if item.lvgl_root == focused_item:
                    return index, item.desc

            # Should never happen
            assert(False)
            return None

    def left_action(self, is_pressed):
        # Don't allow going back when already at the top level
        if not is_pressed:
            if common.ui.is_top_level():
                self.set_result(None)
            else:
                # print('GO BACK UP!')
                self.set_result(None)

    def right_action(self, is_pressed):
        if not is_pressed:
            self.set_result(self.get_focused_item())
