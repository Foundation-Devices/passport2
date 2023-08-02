# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# test_keypad_page.py - tests keypad by showing pressed keys on the display

import lvgl as lv
from pages.page import Page

KeyMap = {
    lv.KEY.ESC: 'x',
    lv.KEY.ENTER: 'y',
    lv.KEY.LEFT: 'l',
    lv.KEY.RIGHT: 'r',
    lv.KEY.UP: 'u',
    lv.KEY.DOWN: 'd',
    lv.KEY.BACKSPACE: '*',
}


class TestKeypadPage(Page):
    def __init__(self):
        from views import Keypad
        from common import keypad

        super().__init__(card_header={'title': 'Keypad Test'},
                         left_micron=None,
                         right_micron=None)

        self.keypad_view = Keypad()
        self.add_child(self.keypad_view)

        keypad.set_intercept_key_cb(self.on_key)

    def attach(self, group):
        from common import keypad

        super().attach(group)
        group.add_obj(self.lvgl_root)
        self.keypad_view.attach(group)
        keypad.disable_nav_and_select_keys(True)

    def detach(self):
        from common import keypad

        self.lvgl_root.remove_event_cb(self.on_key)
        lv.group_remove_obj(self.lvgl_root)
        keypad.set_intercept_key_cb(None)
        keypad.disable_nav_and_select_keys(False)
        self.keypad_view.detach()
        super().detach()

    def on_key(self, key, pressed):
        from common import keypad, ui
        import microns

        # Convert key codes (ASCII or LVGL codes) into characters
        if key in KeyMap:
            self.keypad_view.on_key(KeyMap[key], pressed)
        else:
            self.keypad_view.on_key(chr(key), pressed)

        # Once all done, let the keys be used again
        if self.keypad_view.should_finish():
            keypad.set_intercept_key_cb(None)
            keypad.disable_nav_and_select_keys(False)
            ui.set_right_micron(microns.Forward)
            ui.set_left_micron(microns.Back)
