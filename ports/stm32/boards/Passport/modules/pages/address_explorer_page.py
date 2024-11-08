# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# address_explorer_page.py


import lvgl as lv
from pages import StatusPage
import microns
import common


class AddressExplorerPage(StatusPage):

    def __init__(self,
                 text=None,
                 card_header=None,
                 statusbar=None,
                 left_micron=microns.Back,
                 right_micron=microns.Checkmark,
                 margins=None):
        super().__init__(
            text=text,
            card_header=card_header,
            statusbar=statusbar,
            right_micron=right_micron,
            left_micron=left_micron,
            margins=margins)

    def attach(self, group):
        super().attach(group)
        group.add_obj(self.lvgl_root)
        self.lvgl_root.add_event_cb(self.on_key, lv.EVENT.KEY, None)
        self.prev_top_level = common.ui.set_is_top_level(False)
        # common.keypad.set_intercept_key_cb(self.on_key)
        common.keypad.set_key_repeat(lv.KEY.UP, False)
        common.keypad.set_key_repeat(lv.KEY.DOWN, False)

    def detach(self):
        common.ui.set_is_top_level(self.prev_top_level)
        self.lvgl_root.remove_event_cb(self.on_key)
        lv.group_remove_obj(self.lvgl_root)
        # common.keypad.set_intercept_key_cb(None)
        common.keypad.set_key_repeat(lv.KEY.UP, True)
        common.keypad.set_key_repeat(lv.KEY.DOWN, True)
        super().detach()

    def on_key(self, event):
        key = event.get_key()

        if key == lv.KEY.RIGHT:
            self.set_result('right')
        elif key == lv.KEY.LEFT:
            self.set_result('left')
        elif key == lv.KEY.UP:
            self.set_result('up')
        elif key == lv.KEY.DOWN:
            self.set_result('down')
