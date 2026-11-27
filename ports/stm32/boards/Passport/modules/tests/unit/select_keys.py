# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# A select button acts on the screen it was pressed on. A press made on one screen,
# or while the screen was changing, never confirms or cancels the screen after it.

import common
import lvgl as lv
from keypad import Keypad
from ui import UI


class Page:
    def __init__(self):
        self.actions = []

    def left_action(self, is_pressed):
        self.actions.append(('left', is_pressed))

    def right_action(self, is_pressed):
        self.actions.append(('right', is_pressed))


class FakeUI:
    _select_target = UI._select_target
    on_left_select = UI.on_left_select
    on_right_select = UI.on_right_select

    def __init__(self):
        self.pressed_on = {}
        self.page = None
        self.micron = {'left': False, 'right': False}

    def get_active_page(self):
        return self.page

    def set_left_pressed(self, is_pressed):
        self.micron['left'] = is_pressed

    def set_right_pressed(self, is_pressed):
        self.micron['right'] = is_pressed


class FakeKeypad:
    key_cb = Keypad.key_cb
    check_pending_keys = Keypad.check_pending_keys
    is_global_nav_key = Keypad.is_global_nav_key
    is_animating = Keypad.is_animating

    def __init__(self):
        self.anim_counter = 0
        self.pending_keys = []
        self._disable_nav_and_select_keys = False
        self._enable_global_nav_keys = False


original_ui = common.ui
try:
    ui = FakeUI()
    common.ui = ui
    first, second = Page(), Page()

    # A press and release on the same screen act on it.
    ui.page = first
    ui.on_right_select(True)
    ui.on_right_select(False)
    assert first.actions == [('right', True), ('right', False)]

    # A press on one screen, released once the next is showing, reaches neither: the
    # first never sees the release, and the second never saw the press.
    first.actions = []
    ui.on_right_select(True)
    ui.page = second
    ui.on_right_select(False)
    assert first.actions == [('right', True)]
    assert second.actions == []
    assert not ui.micron['right']

    # The same for the left button, and for a release with no press at all.
    ui.page = first
    ui.on_left_select(True)
    ui.page = second
    ui.on_left_select(False)
    ui.on_right_select(False)
    assert second.actions == []

    # A press and release made while the screen was changing are queued. The release
    # still reaches the new screen's micron, but the screen doesn't act on either.
    keypad = FakeKeypad()
    keypad.pending_keys = [(lv.KEY.ENTER, True), (lv.KEY.ENTER, False),
                           (lv.KEY.ESC, True), (lv.KEY.ESC, False)]
    ui.micron['right'] = True
    keypad.check_pending_keys()
    assert keypad.pending_keys == []
    assert second.actions == []
    assert not ui.micron['right']

    # After that, the new screen works normally.
    ui.on_right_select(True)
    ui.on_right_select(False)
    assert second.actions == [('right', True), ('right', False)]
finally:
    common.ui = original_ui

return_value.write(b'OK')
