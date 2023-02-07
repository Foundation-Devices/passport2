# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# spinner_page.py

from pages import StatusPage


class SpinnerPage(StatusPage):
    def __init__(
            self,
            text=None,
            interactive=False,
            card_header=None,
            statusbar=None,
            left_micron=None, right_micron=None):

        super().__init__(
            text=text,
            show_spinner=True,
            interactive=interactive,
            card_header=card_header,
            statusbar=statusbar,
            left_micron=left_micron,
            right_micron=right_micron)
