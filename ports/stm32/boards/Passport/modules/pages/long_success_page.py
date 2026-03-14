# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# long_success_page.py

import lvgl as lv
from pages import LongTextPage
from styles.colors import DEFAULT_LARGE_ICON_COLOR
import microns


class LongSuccessPage(LongTextPage):
    def __init__(
            self,
            text=None,
            card_header=None,
            statusbar=None,
            left_micron=None,
            right_micron=microns.Checkmark,
            icon=lv.LARGE_ICON_SUCCESS,
            margins=None):
        super().__init__(
            text=text,
            card_header=card_header,
            statusbar=statusbar,
            icon=icon,
            icon_color=DEFAULT_LARGE_ICON_COLOR,
            centered=True,
            left_micron=left_micron,
            right_micron=right_micron,
            margins=margins)
