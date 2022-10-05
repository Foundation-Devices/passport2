# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# chooser_page.py - A page to let the user choose from a list of options.


import lvgl as lv
import microns
from styles.colors import CHOOSER_ICON
from styles import Stylize
from pages import Page
import common

# The `options` parameter is an array of dicts as shown in the following examples:
#
#   options=[{'label': 'Mainnet', value: 'BTC'}, {'label': 'Testnet', value: 'TBTC'}]
#   options=[{'label': 'Off', value: 0}, {'label': '25%', value: 25}, {'label': '50%', value: 50},
#            {'label': '75%', value: 75}, {'label': '100%', value: 100}]


class ChooserPage(Page):
    def __init__(
            self, card_header=None, statusbar=None, options=[],
            initial_value=None, on_change=None,
            icon=None, icon_color=CHOOSER_ICON, text=None, center=False, item_icon=lv.ICON_SMALL_CHECKMARK,
            left_micron=microns.Cancel, right_micron=microns.Checkmark):

        from views import ListItem, View

        super().__init__(
            card_header=card_header,
            statusbar=statusbar,
            flex_flow=lv.FLEX_FLOW.COLUMN,
            left_micron=left_micron,
            right_micron=right_micron)

        self.options = options
        self.initial_value = initial_value
        self.on_change = on_change
        self.icon = icon
        self.icon_color = icon_color
        self.text = text
        self.center = center
        self.item_icon = item_icon

        # If initial value is given, then select it, else o
        if self.initial_value is not None:
            self.selected_idx = self.get_selected_option_index_by_value(self.initial_value)
        else:
            self.selected_idx = 0

        with Stylize(self) as default:
            default.flex_fill()
            default.flex_align(main=lv.FLEX_ALIGN.CENTER, cross=lv.FLEX_ALIGN.CENTER, track=lv.FLEX_ALIGN.CENTER)
            default.pad_row(0)

        # Set non-style props
        self.set_width(lv.pct(100))
        self.set_no_scroll()

        # Add icon if provided
        if icon is not None:
            from views import Icon
            self.icon_view = Icon(self.icon)
            with Stylize(self.icon_view) as default:
                if self.icon_color is not None:
                    default.img_recolor(self.icon_color)
                    default.pad(top=20, bottom=12)
            self.add_child(self.icon_view)

        # Add text if provided
        if self.text is not None:
            from views import Label
            from styles.colors import NORMAL_TEXT

            self.text_view = Label(text=self.text, color=NORMAL_TEXT)
            self.text_view.set_width(lv.pct(100))
            with Stylize(self.text_view) as default:
                default.text_align(lv.TEXT_ALIGN.CENTER)
                default.pad(bottom=12)
            self.add_child(self.text_view)

        # Add a scroll container for the list items, but disable scrollbars until attached
        self.scroll_container = View(flex_flow=lv.FLEX_FLOW.COLUMN)
        self.scroll_container.set_no_scroll()
        self.scroll_container.set_width(lv.pct(100))

        # Adjust scrollbar position
        with Stylize(self.scroll_container, selector=lv.PART.SCROLLBAR) as scrollbar:
            scrollbar.pad(right=0)

        with Stylize(self.scroll_container) as default:
            default.flex_fill()
            default.pad_row(0)

        # Add the list items to the scroll container
        for index in range(len(self.options)):
            option_desc = self.options[index]
            self.scroll_container.add_child(
                ListItem(
                    label=option_desc.get('label'),
                    center=self.center,
                    icon=self.item_icon,
                    is_selected=index == self.selected_idx))

        self.add_child(self.scroll_container)

    def attach(self, group):
        super().attach(group)

        # Ensure scrollbars are enabled again
        self.scroll_container.set_scroll_dir(lv.DIR.VER)

        # Setup gridnav for the layout
        initial_focus = self.scroll_container.children[self.selected_idx].get_lvgl_root()
        lv.gridnav_add(self.scroll_container.lvgl_root, lv.GRIDNAV_CTRL.NONE)
        group.add_obj(self.scroll_container.lvgl_root)  # IMPORTANT: Add this to the group AFTER setting up gridnav
        if initial_focus is not None:
            lv.gridnav_set_focused(self.scroll_container.lvgl_root, initial_focus, False)

        self.scroll_to_selected_option()

    def detach(self):
        lv.group_remove_obj(self.scroll_container.lvgl_root)

        # Hide scrollbars during transitions
        self.scroll_container.set_no_scroll()
        super().detach()

    def scroll_to_selected_option(self):
        """Scrolls the menu list to make the selected option visible."""
        selected = self.scroll_container.children[self.selected_idx].get_lvgl_root()
        if selected is not None:
            sc = self.scroll_container.lvgl_root

            # Reset the current scroll to have a clear reference
            sc.scroll_by(0, sc.get_scroll_y(), lv.ANIM.OFF)

            selected_y = selected.get_y2()
            selected_h = selected.get_height()
            scroll_container_h = sc.get_content_height()

            # Scroll to the selected item if it's outside the visible area
            if selected_y + selected_h > scroll_container_h:
                scroll_y = selected_y - scroll_container_h + selected_h
                sc.scroll_by(0, -scroll_y, lv.ANIM.OFF)

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
                self.scroll_container.children[self.selected_idx].set_selected(False)
                self.selected_idx = self.get_focused_item_index()
                self.scroll_container.children[self.selected_idx].set_selected(True)
                selected_value = self.options[self.selected_idx].get('value')

                # Hook used to allow a side effect (e.g., change screen brightness or change mainnet/testnet mode)
                if self.on_change is not None:
                    self.on_change(selected_value)

                self.set_result(selected_value)
            except Exception as e:
                # print('exception: e={}'.format(e))
                assert(False, '{}'.format(e))
