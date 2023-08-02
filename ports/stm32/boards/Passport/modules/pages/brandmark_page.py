# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# brandmark_page.py - Show a message along with the Passport brandmark.

from pages.status_page import StatusPage
import microns


class BrandmarkPage(StatusPage):
    def __init__(
            self,
            text=None,
            card_header=None,
            statusbar=None,
            left_micron=None,
            right_micron=microns.Checkmark):
        import lvgl as lv

        super().__init__(
            text=text,
            card_header=card_header,
            statusbar=statusbar,
            icon=lv.LARGE_ICON_BRANDMARK,
            left_micron=left_micron,
            right_micron=right_micron)
