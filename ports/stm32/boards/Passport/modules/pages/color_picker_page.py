# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# color_picker_page.py

import lvgl as lv
from styles.style import Stylize
from views import ColorPicker
from pages import Page
import microns


class ColorPickerPage(Page):
    def __init__(self,
                 card_header=None,
                 statusbar=None,
                 left_micron=microns.Back,
                 right_micron=microns.Forward):
        super().__init__(card_header=card_header,
                         statusbar=statusbar,
                         left_micron=left_micron,
                         right_micron=right_micron,
                         flex_flow=lv.FLEX_FLOW.COLUMN)

        # Set non-style props
        self.set_width(lv.pct(100))
        self.set_no_scroll()

        with Stylize(self) as default:
            default.flex_fill()
            default.flex_align(main=lv.FLEX_ALIGN.CENTER, cross=lv.FLEX_ALIGN.CENTER, track=lv.FLEX_ALIGN.CENTER)
            default.pad_row(0)

        self.picker = ColorPicker(initial_color=0x00BDCD)
        self.picker.set_size(lv.pct(100), lv.pct(100))
        self.add_child(self.picker)

    def attach(self, group):
        super().attach(group)
        self.picker.attach(group)

    def detach(self):
        self.picker.detach()
        super().detach()
