# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# spinner_page.py

from pages import StatusPage
import microns


class ProgressPage(StatusPage):
    def __init__(
            self,
            text=None,
            interactive=False,
            card_header=None,
            statusbar=None,
            left_micron=microns.Back,
            right_micron=microns.Forward):
        super().__init__(
            text=text,
            show_progress=True,
            interactive=interactive,
            card_header=card_header,
            statusbar=statusbar,
            left_micron=left_micron,
            right_micron=right_micron)
