# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# micron_bar.py - "Footer" component that shows the contextual button icons and either the card
#                 pagination or a page-specific hint as to the function of the D-pad.

import lvgl as lv
from styles import Stylize
from styles.colors import FD_BLUE, MEDIUM_GREY, MICRON_GREY
from styles.local_style import LocalStyle
from views import View
import common


class MicronBar(View):
    BUTTONS_PAD_BOTTOM = 4
    BUTTONS_PAD_SIDES = 14
    PAGINATION_PAD_BOTTOM = 4
    PAGE_DOT_COLOR = MEDIUM_GREY
    SELECTED_PAGE_DOT_COLOR = FD_BLUE

    def __init__(self, card_descs=[], active_card_idx=0, page_specific_content=View()):
        super().__init__()
        # Save parameters provided to us
        self.card_descs = card_descs
        self.active_card_idx = active_card_idx
        self.page_specific_content = page_specific_content
        self.force_show = False

        self.left_micron = None
        self.right_micron = None

        self.set_no_scroll()

        # Page-specific content
        with Stylize(self.page_specific_content) as default:
            default.align(lv.ALIGN.BOTTOM_MID)
        self.page_specific_content.set_y(-self.PAGINATION_PAD_BOTTOM)
        self.add_child(self.page_specific_content)

        # Render the micron page dots
        self.page_dots_container = View(flex_flow=lv.FLEX_FLOW.ROW)
        with Stylize(self.page_dots_container) as default:
            default.flex_align(main=lv.FLEX_ALIGN.CENTER, track=lv.FLEX_ALIGN.CENTER)
        self.page_dots_container.set_y(-1)
        self.page_dots_container.set_size(lv.pct(80), 20)
        self.update_pagination_dots()

        with Stylize(self.page_dots_container) as default:
            default.align(lv.ALIGN.BOTTOM_MID)
        self.add_child(self.page_dots_container)

    def show_pagination(self):
        return self.card_descs is not None and (self.force_show or (common.ui is not None and common.ui.is_top_level()))

    def update_pagination_dots(self):
        # # Delete existing dots
        if self.page_dots_container.is_mounted():
            if self.page_dots_container.children is not None:
                self.page_dots_container.unmount_children()
                # i = 0
                # for child in self.page_dots_container.children:
                #     child.unmount()
                #     i += 1
                self.page_dots_container.set_children([])

        # Only draw the dots if there is more than one page
        if len(self.card_descs) > 1:
            col_padding = None
            num_dots = len(self.card_descs)
            if num_dots <= 12:
                col_padding = 5
            elif num_dots <= 14:
                col_padding = 4
            elif num_dots <= 18:
                col_padding = 1
            else:
                col_padding = 0

            with LocalStyle(self.page_dots_container) as style:
                style.pad_col(col_padding)

            for i in range(len(self.card_descs)):
                # print('Card dot...')
                card_desc = self.card_descs[i]
                if i == self.active_card_idx:
                    # log('SELECTED')
                    color = FD_BLUE
                else:
                    # log('NOT SELECTED')
                    color = MICRON_GREY
                if card_desc is not None and callable(card_desc.get('page_micron')):
                    icon = card_desc.get('page_micron')()
                    with Stylize(icon) as default:
                        default.img_recolor(color)

                    # print('icon={}'.format(icon))
                    self.page_dots_container.add_child(icon)

                    if self.page_dots_container.is_mounted():
                        # print('mounting icon')
                        icon.mount(self.page_dots_container.lvgl_root)

    def mount(self, lvgl_parent):
        super().mount(lvgl_parent)
        self.show_hide_pagination()

    def show_hide_pagination(self):
        # print('show_hide_pagination()')
        with LocalStyle(self.page_dots_container) as style:
            style.opa(255 if self.show_pagination() else 0)
        with LocalStyle(self.page_specific_content) as style:
            style.opa(255 if not self.show_pagination() else 0)

    def set_page_specific_content(self, content):
        if content is None:
            content = View()
        self.page_specific_content = content
        if self.is_mounted():
            self.show_hide_pagination()

    def set_active_idx(self, active_idx):
        if active_idx is not None:
            self.active_card_idx = active_idx
        self.update_pagination_dots()

    # Set to None to hide pagination

    def set_cards(self, card_descs, active_idx=None, force_show=False):
        original_card_descs = self.card_descs
        # print('**** MicronBar set_cards(): cards={} active_idx={}'.format(card_descs, active_idx))
        self.card_descs = card_descs
        self.force_show = force_show
        if active_idx is not None:
            self.active_card_idx = active_idx
        self.update_pagination_dots()
        self.show_hide_pagination()

        return original_card_descs

    def set_left_pressed(self, is_pressed):
        if self.left_micron is not None:
            self.left_micron.set_pressed(is_pressed)

    def set_right_pressed(self, is_pressed):
        if self.right_micron is not None:
            self.right_micron.set_pressed(is_pressed)

    # NOTE: We are not adding the microns as children to the Views here, but for consistency
    #       we probably should.
    def set_left_micron(self, micron):
        if self.left_micron is not None and self.left_micron.is_mounted():
            self.left_micron.unmount()

        if micron is not None:
            # IMPORTANT: Microns must be passed as functions, so we call it here to instantiate it
            self.left_micron = micron()
            with Stylize(self.left_micron) as default:
                default.align(lv.ALIGN.BOTTOM_LEFT)
            self.left_micron.set_pos(self.BUTTONS_PAD_SIDES, -self.BUTTONS_PAD_BOTTOM)
            self.left_micron.mount(self.lvgl_root)

    def set_right_micron(self, micron):
        if self.right_micron is not None and self.right_micron.is_mounted():
            self.right_micron.unmount()

        if micron is not None:
            # IMPORTANT: Microns must be passed as functions, so we call it here to instantiate it
            self.right_micron = micron()
            with Stylize(self.right_micron) as default:
                default.align(lv.ALIGN.BOTTOM_RIGHT)
            self.right_micron.set_pos(-self.BUTTONS_PAD_SIDES, -self.BUTTONS_PAD_BOTTOM)
            self.right_micron.mount(self.lvgl_root)
