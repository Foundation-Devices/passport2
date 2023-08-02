# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# long_question_page.py

import lvgl as lv
from pages.long_text_page import LongTextPage
from styles.colors import DEFAULT_LARGE_ICON_COLOR
import microns


class LongQuestionPage(LongTextPage):
    def __init__(
        self,
        text=None,
        icon=lv.LARGE_ICON_QUESTION,
        icon_color=DEFAULT_LARGE_ICON_COLOR,
        card_header=None,
        statusbar=None,
        left_micron=microns.Cancel,
        right_micron=microns.Checkmark
    ):
        super().__init__(
            text=text,
            icon=icon,
            icon_color=icon_color,
            card_header=card_header,
            statusbar=statusbar,
            centered=True,
            left_micron=left_micron,
            right_micron=right_micron)
