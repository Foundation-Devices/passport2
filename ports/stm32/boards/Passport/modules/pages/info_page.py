# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# info_page.py

import lvgl as lv
from pages.status_page import StatusPage
import microns


class InfoPage(StatusPage):
    def __init__(
            self, text=None, icon=lv.LARGE_ICON_INFO, card_header=None, statusbar=None, left_micron=None,
            right_micron=microns.Checkmark):
        from styles.colors import DEFAULT_LARGE_ICON_COLOR

        super().__init__(
            text=text,
            icon=icon,
            icon_color=DEFAULT_LARGE_ICON_COLOR,
            card_header=card_header,
            statusbar=statusbar,
            left_micron=left_micron,
            right_micron=right_micron)
