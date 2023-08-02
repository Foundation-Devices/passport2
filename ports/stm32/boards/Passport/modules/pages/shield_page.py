# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# info_page.py

from pages.status_page import StatusPage
import microns


class ShieldPage(StatusPage):
    def __init__(
            self,
            text=None,
            centered=True,
            card_header={'title': 'Security Check'},
            statusbar=None,
            left_micron=microns.Back,
            right_micron=microns.Forward):
        import lvgl as lv
        from styles.colors import DEFAULT_LARGE_ICON_COLOR

        super().__init__(
            text=text,
            icon=lv.LARGE_ICON_SHIELD,
            icon_color=DEFAULT_LARGE_ICON_COLOR,
            centered=centered,
            card_header=card_header,
            statusbar=statusbar,
            left_micron=left_micron,
            right_micron=right_micron)
