# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Once a progress page has been drawn, moving its arc and percentage takes nothing from
# the heap: LVGL keeps its small draw buffers and circle cache between refreshes. Late in
# a large PSBT the heap can be too fragmented to supply them again, and the redraw would
# fail.

import common
import lvgl as lv
import micropython
from display import Display
from pages import StatusPage


class UI:
    def set_left_micron(self, micron):
        pass

    def set_right_micron(self, micron):
        pass


class Keypad:
    def set_active_page(self, page):
        pass


def test_redraw():
    Display()
    original_ui, original_keypad = common.ui, common.keypad
    common.ui, common.keypad = UI(), Keypad()
    parent = lv.obj(lv.scr_act())
    parent.set_size(230, 220)
    parent.set_style_pad_all(0, 0)
    parent.set_flex_flow(lv.FLEX_FLOW.COLUMN)
    group = lv.group_create()
    page = StatusPage(text='Validating transaction', show_progress=True, interactive=False)
    page.mount(parent)
    page.attach(group)
    page.set_progress(40)
    lv.refr_now(None)
    # The next step moves the arc and the percentage, as during a PSBT.
    page.set_progress(41)
    # Any allocation from here on raises MemoryError.
    micropython.heap_lock()
    try:
        lv.refr_now(None)
    finally:
        micropython.heap_unlock()
    # A MemoryError from inside LVGL's drawing leaves it unable to delete objects
    # safely, so this cleanup only runs after a redraw that worked.
    page.detach()
    page.unmount()
    parent.delete()
    group._del()
    common.ui, common.keypad = original_ui, original_keypad


test_redraw()
return_value.write(b'OK')
