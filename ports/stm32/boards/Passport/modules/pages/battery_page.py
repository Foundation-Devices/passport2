# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# info_page.py

import lvgl as lv
from pages import StatusPage
from styles.colors import FD_BLUE, FD_BLUE_HEX
import microns


class BatteryPage(StatusPage):
    def __init__(self, text=None, card_header={'title': 'Battery'},
                 statusbar=None, left_micron=None, right_micron=microns.Checkmark):
        from common import ui

        super().__init__(
            progress_color=FD_BLUE,
            show_progress=True,
            percent=ui.battery_level,
            card_header=card_header,
            statusbar=statusbar,
            left_micron=left_micron,
            right_micron=right_micron)

    def update_battery(self):
        from common import ui
        self.set_progress(ui.battery_level)

    def on_timer(self, _t):
        self.update_battery()

    def attach(self, group):
        super().attach(group)

        # Create a timer to update the battery
        self.timer = lv.timer_create(self.on_timer, 5000, None)

    def detach(self):
        super().detach()

        if self.timer is not None:
            self.timer._del()
            self.timer = None
