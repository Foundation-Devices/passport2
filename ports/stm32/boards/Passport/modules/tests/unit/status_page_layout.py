# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# A status page centers content that fits. Content that doesn't fit starts at the top,
# so none of it is above the page where it couldn't be scrolled to.

import common
import lvgl as lv
from display import Display
from pages import ErrorPage


class UI:
    def set_left_micron(self, micron):
        pass

    def set_right_micron(self, micron):
        pass


class Keypad:
    def set_active_page(self, page):
        pass


def coords(view):
    area = lv.area_t()
    view.lvgl_root.get_coords(area)
    return area


def check(parent, group, text, overflow):
    page = ErrorPage(text=text)
    page.mount(parent)
    page.attach(group)
    try:
        container = page.container
        container.lvgl_root.update_layout()
        box = coords(container)
        icon = coords(page.center_content)
        label = coords(page.text_view)
        assert container.lvgl_root.get_scroll_top() == 0
        assert (container.lvgl_root.get_scroll_bottom() > 0) == overflow
        assert icon.y1 >= box.y1, (icon.y1, box.y1)
        if overflow:
            assert icon.y1 - box.y1 < 5, (icon.y1, box.y1)
        else:
            # Centered: the same space above the icon as below the text.
            above = icon.y1 - box.y1
            below = box.y2 - label.y2
            assert above > 20 and abs(above - below) <= 2, (above, below)
    finally:
        page.detach()
        page.unmount()


def test_layout():
    Display()
    original_ui, original_keypad = common.ui, common.keypad
    common.ui, common.keypad = UI(), Keypad()
    parent = lv.obj(lv.scr_act())
    parent.set_size(230, 220)
    parent.set_style_pad_all(0, 0)
    parent.set_flex_flow(lv.FLEX_FLOW.COLUMN)
    group = lv.group_create()
    try:
        check(parent, group, 'Saved', False)
        check(parent, group, 'This transaction has too many inputs for Passport to sign.\n\n'
                             'Split it into smaller transactions in your wallet coordinator '
                             'and try again.\n\n' * 3, True)
    finally:
        parent.delete()
        group._del()
        common.ui, common.keypad = original_ui, original_keypad


test_layout()
return_value.write(b'OK')
