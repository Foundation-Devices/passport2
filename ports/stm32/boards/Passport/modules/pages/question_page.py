# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# question_page.py

import lvgl as lv
from pages import StatusPage
from styles.colors import FD_BLUE
import microns


class QuestionPage(StatusPage):
    def __init__(
            self, text=None, card_header=None, statusbar=None, left_micron=microns.Cancel,
            right_micron=microns.Checkmark):
        super().__init__(
            text=text,
            icon=lv.LARGE_ICON_QUESTION,
            icon_color=FD_BLUE,
            card_header=card_header,
            statusbar=statusbar,
            left_micron=left_micron,
            right_micron=right_micron)
