# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# long_error_page.py

import lvgl as lv
from pages import LongTextPage
from styles.colors import COPPER
import microns


class LongErrorPage(LongTextPage):
    def __init__(
            self,
            text=None,
            card_header=None,
            statusbar=None,
            left_micron=None,
            right_micron=microns.Checkmark):
        super().__init__(
            text=text,
            card_header=card_header,
            statusbar=statusbar,
            centered=True,
            icon=lv.LARGE_ICON_ERROR,
            icon_color=COPPER,
            left_micron=left_micron,
            right_micron=right_micron)
