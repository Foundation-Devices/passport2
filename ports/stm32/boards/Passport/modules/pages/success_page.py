# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# success_page.py

import lvgl as lv
from pages import StatusPage
from styles.colors import DEFAULT_LARGE_ICON_COLOR
import microns


class SuccessPage(StatusPage):
    def __init__(
            self,
            text=None,
            card_header=None,
            statusbar=None,
            left_micron=None,
            right_micron=microns.Checkmark,
            icon=lv.LARGE_ICON_SUCCESS,
            margins=None,
            custom_view=None):
        super().__init__(
            text=text,
            card_header=card_header,
            statusbar=statusbar,
            icon=icon,
            icon_color=DEFAULT_LARGE_ICON_COLOR,
            left_micron=left_micron,
            right_micron=right_micron,
            margins=margins,
            custom_view=custom_view)
