# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# info_page.py

import lvgl as lv
from pages import StatusPage
from styles.colors import FD_BLUE
import microns


class InfoPage(StatusPage):
    def __init__(
            self, text=None, icon=lv.LARGE_ICON_INFO, card_header=None, statusbar=None, left_micron=None,
            right_micron=microns.Checkmark):
        super().__init__(
            text=text,
            icon=icon,
            icon_color=FD_BLUE,
            card_header=card_header,
            statusbar=statusbar,
            left_micron=left_micron,
            right_micron=right_micron)
