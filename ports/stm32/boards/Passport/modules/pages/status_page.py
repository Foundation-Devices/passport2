# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# status_page.py

import lvgl as lv
from styles.style import Stylize
from views import Arc, Label, View, Icon, Spinner
from pages import Page
from styles.colors import DEFAULT_SPINNER, TEXT_GREY
import microns
import common
import passport


class StatusPage(Page):
    CENTER_SIZE = 100

    def __init__(self, text=None, icon=None, icon_color=None, show_progress=False, percent=0,
                 centered=True, show_spinner=False, interactive=True, card_header=None,
                 statusbar=None, left_micron=microns.Back, right_micron=microns.Forward,
                 use_left_button=True):
        super().__init__(card_header=card_header,
                         statusbar=statusbar,
                         left_micron=left_micron,
                         right_micron=right_micron)

        if not passport.IS_COLOR:
            self.CENTER_SIZE = 75

        self.text = text
        self.page_idx = 0
        self.icon = icon
        self.icon_color = icon_color

        self.show_progress = show_progress
        self.percent = percent

        self.centered = centered
        self.show_spinner = show_spinner
        self.interactive = interactive
        self.use_left_button = use_left_button

        self.is_list_mode = isinstance(self.text, list)

        # Make a container so it's easier to update without affecting the Page parent, and also in case we
        # need to be able to scroll.
        self.container = View(flex_flow=lv.FLEX_FLOW.COLUMN)
        self.container.set_size(lv.pct(100), lv.pct(100))
        with Stylize(self.container) as default:
            default.pad(left=8, right=8)
            default.pad_row(20)
            default.flex_align(main=lv.FLEX_ALIGN.CENTER, cross=lv.FLEX_ALIGN.CENTER, track=lv.FLEX_ALIGN.CENTER)
        self.set_children([self.container])

        with Stylize(self.container, selector=lv.PART.SCROLLBAR) as scrollbar:
            scrollbar.pad(right=0)

        self.update()

    def update(self):
        if self.is_mounted():
            self.container.unmount_children()
            self.container.set_children([])

        # Update microns in a special way for array text
        if self.is_list_mode:
            common.ui.set_left_micron(microns.Back)
            common.ui.set_right_micron(microns.Forward)
            if self.page_idx == 0:
                common.ui.set_left_micron(self.left_micron)
            elif self.page_idx == len(self.text):
                common.ui.set_right_micron(self.right_micron)

        # center container so we can center the icon or progress in it
        self.center_container = View()
        self.center_container.set_size(lv.pct(100), lv.SIZE.CONTENT)

        self.center_content = None
        if self.icon is not None:
            self.center_content = Icon(self.icon)
            self.center_content.set_size(self.icon.header.w, self.icon.header.h)
            self.center_content.set_no_scroll()
            with Stylize(self.center_content) as default:
                if self.icon_color is not None:
                    default.img_recolor(self.icon_color)

        elif self.show_progress:
            self.center_content = Arc(start=0, end=0, color=DEFAULT_SPINNER)
            self.center_content.set_size(self.CENTER_SIZE, self.CENTER_SIZE)

            self.progress_label = Label(text=self.get_percent_text(), color=TEXT_GREY)
            self.center_container.add_child(self.progress_label)
            with Stylize(self.progress_label) as default:
                default.align(lv.ALIGN.CENTER)
            self.update_progress()

        elif self.show_spinner:
            self.center_content = Spinner()
            self.center_content.set_size(self.CENTER_SIZE, self.CENTER_SIZE)

        if self.center_content is not None:
            with Stylize(self.center_content) as default:
                default.align(lv.ALIGN.CENTER)

            self.center_container.add_child(self.center_content)
            self.center_container.set_no_scroll()
            self.container.add_child(self.center_container)

        if self.text is not None:
            if self.is_list_mode:
                text = self.text[self.page_idx]
            else:
                text = self.text

            self.text_view = Label(text=text, color=TEXT_GREY)
            self.text_view.set_width(lv.pct(100))
            with Stylize(self.text_view) as default:
                if self.centered:
                    default.text_align(lv.TEXT_ALIGN.CENTER)
            self.container.add_child(self.text_view)

        if self.is_mounted():
            self.container.mount_children()

    def update_progress(self):
        self.progress_label.set_text(self.get_percent_text())
        angle = int(360 * (self.percent / 100))

        # center_content is an Arc when using progress
        assert(isinstance(self.center_content, Arc))
        self.center_content.set_end_angle(angle)

    def get_percent_text(self):
        return '{}%'.format(int(self.percent))

    def set_text(self, text):
        self.text = text
        self.update()

    def set_icon(self, icon, color=None):
        self.icon = icon
        if color is not None:
            self.icon_color = color
        self.show_progress = False
        self.update()

    def set_progress(self, percent):
        self.percent = percent
        self.show_progress = True
        self.update()

    def attach(self, group):
        super().attach(group)

        # Setup gridnav for the layout
        lv.gridnav_add(self.lvgl_root, lv.GRIDNAV_CTRL.NONE)
        group.add_obj(self.lvgl_root)  # IMPORTANT: Add this to the group AFTER setting up gridnav

    def detach(self):
        lv.group_remove_obj(self.lvgl_root)
        super().detach()

    def right_action(self, is_pressed):
        if self.interactive:
            if not is_pressed:
                if self.is_list_mode and self.page_idx < len(self.text) - 1:
                    self.page_idx += 1
                    self.update()
                else:
                    self.set_result(True)

    def left_action(self, is_pressed):
        if self.interactive and self.use_left_button:
            if not is_pressed:
                if self.is_list_mode and self.page_idx > 0:
                    self.page_idx -= 1
                    self.update()
                else:
                    self.set_result(False)
