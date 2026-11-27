# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# A long text page scrolls its icon together with its text, instead of keeping the
# icon at the top while the text scrolls under it. The gap between the icon and the
# text stays 8 px.

import common
import lvgl as lv
from display import Display
from pages import LongSuccessPage


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
    page = LongSuccessPage(text=text)
    page.mount(parent)
    page.attach(group)
    try:
        container = page.container.lvgl_root
        page.lvgl_root.update_layout()
        icon = coords(page.icon_view)
        label = coords(page.text)
        # From the bottom of the icon image, not of its padding, to the top of the text.
        icon_bottom = icon.y2 - page.icon_view.lvgl_root.get_style_pad_bottom(lv.PART.MAIN)
        assert label.y1 - icon_bottom - 1 == 8, (icon_bottom, label.y1)
        bottom = container.get_scroll_bottom()
        assert (bottom > 0) == overflow, bottom
        if overflow:
            # Scrolled to the end, the icon has moved up as far as the text.
            container.scroll_to_y(bottom, lv.ANIM.OFF)
            page.lvgl_root.update_layout()
            assert coords(page.icon_view).y1 == icon.y1 - bottom, (icon.y1, bottom)
            assert coords(page.text).y1 == label.y1 - bottom, (label.y1, bottom)
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
        check(parent, group, 'Signed transaction saved to microSD.\n\n' * 8, True)
    finally:
        parent.delete()
        group._del()
        common.ui, common.keypad = original_ui, original_keypad


test_layout()
return_value.write(b'OK')
