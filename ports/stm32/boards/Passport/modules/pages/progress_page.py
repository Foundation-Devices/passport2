# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
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
            right_micron=microns.Forward,
            spinner_first=False):
        # spinner_first: show a spinner until the first set_progress().
        super().__init__(
            text=text,
            show_progress=not spinner_first,
            show_spinner=spinner_first,
            interactive=interactive,
            card_header=card_header,
            statusbar=statusbar,
            left_micron=left_micron,
            right_micron=right_micron)

    def attach(self, group):
        import common

        super().attach(group)
        # Never auto-shutdown during progress
        common.settings.set_volatile('shutdown_timeout', 0)

    def detach(self):
        import common
        from keypad import feedback

        # reset auto-shutdown timer before returning to normal setting
        feedback()
        common.settings.clear_volatile('shutdown_timeout')
        super().detach()
