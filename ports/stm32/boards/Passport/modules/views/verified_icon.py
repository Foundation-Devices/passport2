# SPDX-FileCopyrightText: © 2024 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# verified_icon.py - custom icon for address verification


import lvgl as lv
from views import View, Icon, Label
from styles.style import Stylize
from styles.colors import WHITE, DEFAULT_LARGE_ICON_COLOR
import passport


class VerifiedIcon(View):
    def __init__(self, icon_color=DEFAULT_LARGE_ICON_COLOR):

        self.icon_color = icon_color
        super().__init__(flex_flow=lv.FLEX_FLOW.ROW)

        size = 50 if passport.IS_COLOR else 55
        self.set_size(lv.pct(size), lv.SIZE.CONTENT)
        with Stylize(self) as default:
            default.flex_align(main=lv.FLEX_ALIGN.CENTER)
            if self.icon_color is not None:
                default.bg_color(self.icon_color)
            default.radius(20)
        self.message_icon = Icon(lv.ICON_CHECKMARK, color=WHITE)
        with Stylize(self.message_icon) as default:
            default.flex_align(cross=lv.FLEX_ALIGN.CENTER)
            default.pad(left=7, right=-2, top=8, bottom=6)
        self.add_child(self.message_icon)
        self.message = Label(text='Verified', color=WHITE, center=True)
        with Stylize(self.message) as default:
            default.flex_align(cross=lv.FLEX_ALIGN.CENTER)
            default.pad(top=9, right=7, bottom=3)
        self.add_child(self.message)
