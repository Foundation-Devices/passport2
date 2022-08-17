# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# brightness_adjustable_page.py

import lvgl as lv
import common
import microns
from pages import Page

brightness_levels = [5, 25, 50, 75, 100]


class BrightnessAdjustablePage(Page):
    """
    A page that allow updating the brightness of the screen

    The brightness can be changed using the up and down keys.

    The method on_key needs to be called by the subclassed page,
    for examplem by using Keypad.set_intercept_key_cb.
    """

    def __init__(self,
                 card_header=None,
                 statusbar=None,
                 left_micron=microns.Back,
                 right_micron=microns.Checkmark):
        super().__init__(card_header=card_header,
                         statusbar=statusbar,
                         left_micron=left_micron,
                         right_micron=right_micron)

    def attach(self, group):
        super().attach(group)

        self.prev_brightness = common.system.get_screen_brightness(100)

        # We set the screen brightness to the level the user last left it at when on this page
        self.curr_brightness = common.settings.get('last_qr_brightness',
                                                   self.prev_brightness)
        common.display.set_brightness(self.curr_brightness)

        try:
            self.curr_brightness_idx = brightness_levels.index(self.curr_brightness)
        except ValueError:
            self.curr_brightness_idx = 4

    def detach(self):
        common.settings.set('last_qr_brightness', self.curr_brightness)

        # Restore the previous screen brightness
        common.display.set_brightness(self.prev_brightness)

        super().detach()

    def on_key(self, key, pressed):
        """
        Handle up and down keys to change the brightness

        Must be called when overriden.
        """

        import common

        if pressed:
            # Handle brightness changes
            if key == lv.KEY.UP:
                if self.curr_brightness_idx < len(brightness_levels) - 1:
                    self.curr_brightness_idx += 1
                    self.curr_brightness = brightness_levels[self.curr_brightness_idx]
                    common.display.set_brightness(self.curr_brightness)
            elif key == lv.KEY.DOWN:
                if self.curr_brightness_idx > 0:
                    self.curr_brightness_idx -= 1
                    self.curr_brightness = brightness_levels[self.curr_brightness_idx]
                    common.display.set_brightness(self.curr_brightness)

