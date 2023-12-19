# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# long_text_page.py

import lvgl as lv
from styles.style import Stylize
from views import Label, View, Icon
from pages import Page
from styles.colors import TEXT_GREY, SCROLLBAR_BG_COLOR
import microns
import passport


class MultipleAlignmentPage(Page):
    def __init__(self,
                 icon=None,
                 icon_color=None,
                 text_list=[],
                 card_header=None,
                 statusbar=None,
                 left_micron=microns.Back,
                 right_micron=microns.Forward,
                 long_text=True):
        super().__init__(
            card_header=card_header,
            statusbar=statusbar,
            left_micron=left_micron,
            right_micron=right_micron,
            flex_flow=lv.FLEX_FLOW.COLUMN)
        self.text_list = text_list
        self.icon = icon
        self.icon_color = icon_color

        # Set non-style props
        self.set_width(lv.pct(100))
        self.set_no_scroll()

        with Stylize(self) as default:
            default.flex_fill()
            default.flex_align(main=lv.FLEX_ALIGN.CENTER, cross=lv.FLEX_ALIGN.CENTER, track=lv.FLEX_ALIGN.CENTER)
            default.pad_row(0)

        # Add an icon if provided
        if self.icon is not None:
            self.icon_view = Icon(self.icon, color=self.icon_color)
            with Stylize(self.icon_view) as default:
                default.pad(top=16, bottom=8)
            self.add_child(self.icon_view)

        self.container = View(flex_flow=lv.FLEX_FLOW.COLUMN)
        self.container.set_width(lv.pct(100))
        with Stylize(self.container) as default:
            default.flex_fill()
            default.pad(left=8, right=8)

        with Stylize(self.container, selector=lv.PART.SCROLLBAR) as scrollbar:
            if not passport.IS_COLOR:
                scrollbar.bg_color(SCROLLBAR_BG_COLOR)

        for text in self.text_list:
            next_text = Label(text=text['text'])

            next_text.set_width(lv.pct(100))
            with Stylize(next_text) as default:
                # default.text_align(lv.TEXT_ALIGN.CENTER)
                default.flex_align(main=lv.FLEX_ALIGN.CENTER)
                default.text_color(TEXT_GREY)
                # default.bg_color(GREEN, 128)
                if text.get('centered', True):
                    default.text_align(lv.TEXT_ALIGN.CENTER)

            self.container.add_child(next_text)

        self.add_child(self.container)

    def attach(self, group):
        super().attach(group)

        # Setup gridnav for the layout
        lv.gridnav_add(self.lvgl_root, lv.GRIDNAV_CTRL.NONE)
        group.add_obj(self.lvgl_root)  # IMPORTANT: Add this to the group AFTER setting up gridnav

    def detach(self):
        lv.group_remove_obj(self.lvgl_root)
        super().detach()
