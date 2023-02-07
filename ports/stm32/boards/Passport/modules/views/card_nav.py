# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# card_nav.py - Top-level, card-based navigation.  Cards animate left/right as they are shown/hidden.


from constants import (STATUSBAR_HEIGHT, CARD_PAD_BOTTOM, CARD_PAD_LEFT, CARD_PAD_RIGHT,
                       MICRON_BAR_HEIGHT)
import lvgl as lv
import common
from styles import Stylize
from styles.colors import CARD_HEADER_TEXT, LIGHT_GREY, BLACK, CARD_HEADER_TEXT
from views import View, Card, MicronBar
from animations import card_anim


class CardNav(View):
    def __init__(self):
        super().__init__()
        self.active_card = None
        self.active_idx = None
        self.card_descs = []

        with Stylize(self) as default:
            default.pad_row(0)  # Remove space between card_container and micron bar
        self.set_width(lv.pct(100))
        self.set_height(lv.pct(100))

        # Set non-style props
        # Make sure no scrollbar appears when animating cards, as we actually temporarily make the view
        # larger than would fit on screen, so a scrollbar appears without this.
        self.set_no_scroll()

        # Micron bar
        self.micron_bar = MicronBar(
            card_descs=self.card_descs, active_card_idx=self.active_idx)

        with Stylize(self.micron_bar) as default:
            # default.bg_color(RED, 128)
            default.align(lv.ALIGN.BOTTOM_MID)
        self.micron_bar.set_size(lv.pct(100), MICRON_BAR_HEIGHT)

        self.set_children([self.micron_bar])

    def has_cards(self):
        return len(self.card_descs) > 0

    def detach(self):
        self.lvgl_root.remove_event_cb(self.on_back)
        if self.has_cards():
            self.active_card.detach()
        super().detach()

    def set_card_pos(self, card, is_offscreen=False):
        card_y = 0

        if is_offscreen:
            card.set_pos(CARD_PAD_LEFT + common.display.WIDTH, card_y)
        else:
            card.set_pos(CARD_PAD_LEFT, card_y)
        card.set_size(common.display.WIDTH - (CARD_PAD_LEFT + CARD_PAD_RIGHT), common.display.HEIGHT -
                      (CARD_PAD_BOTTOM + STATUSBAR_HEIGHT + card_y))

    def set_cards(self, card_descs, active_idx=0):
        # TODO: Need to remove/unset/delete any Cards that were already here
        self.card_descs = card_descs
        self.active_idx = active_idx
        assert(active_idx >= 0 and active_idx < len(card_descs))

        # Update the micron bar pagination icons
        self.micron_bar.set_cards(self.card_descs, active_idx=active_idx)

    # TODO: REFACTOR THE 3 FUNCTIONS BELOW AS THEY ARE VERY SIMILAR

    def push_card(self, new_card_desc, new_index):
        from common import keypad

        keypad.set_is_animating(True)

        curr_card = self.active_card

        # Detach the old card before the animation starts
        if curr_card is not None:
            curr_card.detach()

        # Mount the new card, but don't attach yet
        new_card = Card(
            title=new_card_desc.get('title'),
            icon=new_card_desc.get('icon'),
            right_icon=new_card_desc.get('right_icon'),
            page_micron=new_card_desc.get('page_micron', lambda: None),
            right_text=new_card_desc.get('right_text'),
            bg_color=new_card_desc.get('bg_color', BLACK),
            header_color=new_card_desc.get('header_color', LIGHT_GREY),
            header_fg_color=new_card_desc.get('header_fg_color', CARD_HEADER_TEXT))

        new_card_widget = new_card.mount(self.lvgl_root)
        new_card.attach(self.group)
        self.set_card_pos(new_card_widget, is_offscreen=True)
        self.micron_bar.set_active_idx(new_index)

        def done_cb():
            if curr_card is not None:
                curr_card.unmount()

            keypad.set_is_animating(False)

        self.active_card = new_card
        card_anim.push_card(self.active_card_widget, CARD_PAD_LEFT, new_card_widget, done_cb=done_cb)
        self.active_card_widget = new_card_widget

    def pop_card(self, new_card_desc, new_index):
        from common import keypad

        keypad.set_is_animating(True)

        curr_card = self.active_card

        # Detach the old card before the animation starts
        if curr_card is not None:
            curr_card.detach()

        # Mount the new card, but don't attach yet
        new_card = Card(
            title=new_card_desc.get('title'),
            icon=new_card_desc.get('icon'),
            right_icon=new_card_desc.get('right_icon'),
            page_micron=new_card_desc.get('page_micron', lambda: None),
            right_text=new_card_desc.get('right_text'),
            bg_color=new_card_desc.get('bg_color', BLACK),
            header_color=new_card_desc.get('header_color', LIGHT_GREY),
            header_fg_color=new_card_desc.get('header_fg_color', CARD_HEADER_TEXT))

        new_card_widget = new_card.mount(self.lvgl_root)
        new_card.attach(self.group)
        self.set_card_pos(new_card_widget, is_offscreen=True)
        self.micron_bar.set_active_idx(new_index)

        def done_cb():
            if curr_card is not None:
                curr_card.unmount()

            keypad.set_is_animating(False)

        self.active_card = new_card
        card_anim.pop_card(self.active_card_widget, CARD_PAD_LEFT, new_card_widget, done_cb=done_cb)
        self.active_card_widget = new_card_widget

    # Replace/set card immediately with no animation
    def replace_card(self, new_card_desc):
        curr_card = self.active_card

        # Detach the old card before the animation starts
        if curr_card is not None:
            curr_card.detach()
            curr_card.unmount()

        # Mount and attach the new card
        new_card = Card(
            title=new_card_desc.get('title'),
            icon=new_card_desc.get('icon'),
            right_icon=new_card_desc.get('right_icon'),
            page_micron=new_card_desc.get('page_micron', lambda: None),
            right_text=new_card_desc.get('right_text'),
            initial_page=new_card_desc.get('initial_page'),
            bg_color=new_card_desc.get('bg_color', BLACK),
            header_color=new_card_desc.get('header_color', LIGHT_GREY),
            header_fg_color=new_card_desc.get('header_fg_color', CARD_HEADER_TEXT))

        new_card_widget = new_card.mount(self.lvgl_root)
        self.set_card_pos(new_card_widget)
        self.active_card = new_card
        self.active_card_widget = new_card_widget
        new_card.attach(self.group)
