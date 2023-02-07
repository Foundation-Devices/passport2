# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# account_details_page.py - Show a page with information for the current account.

import lvgl as lv
from pages import Page
from styles.style import Stylize
from views import View, Label
import microns
from styles.colors import HIGHLIGHT_TEXT_HEX, TEXT_GREY
from micropython import const
import common

_NUM_COLUMNS = const(2)


class SeedWordsListPage(Page):
    def __init__(
            self,
            words=[],
            card_header=None,
            statusbar=None,
            left_micron=None,
            right_micron=microns.Checkmark):

        self.words = words
        self.page_idx = 0
        self.prev_card_descs = None
        self.prev_card_idx = None

        if len(self.words) == 24:
            self.num_pages = 2
            right_micron = microns.Forward
        else:
            self.num_pages = 1
            right_micron = microns.Checkmark

        super().__init__(
            card_header=card_header,
            statusbar=statusbar,
            left_micron=left_micron,
            right_micron=right_micron,
            flex_flow=None)

        self.set_size(lv.pct(100), lv.pct(100))

        # Put it in a container so we can center it
        self.container = View(flex_flow=lv.FLEX_FLOW.ROW)
        self.container.set_size(lv.pct(100), lv.SIZE.CONTENT)
        self.add_child(self.container)

        self.container.set_height(lv.pct(100))
        with Stylize(self.container) as default:
            default.flex_fill()
            # default.bg_color(RED, opa=64)
            if len(words) == 24:
                default.pad(top=8, bottom=8)
            else:
                default.align(lv.ALIGN.CENTER)
            default.pad_col(4)

        with Stylize(self, selector=lv.PART.SCROLLBAR) as scrollbar:
            scrollbar.pad(right=0)

        self.update()

    def get_card_title(self):
        return 'Page {} of {}'.format(self.page_idx + 1, self.num_pages)

    def update(self):
        from utils import recolor
        if self.is_mounted():
            self.container.unmount_children()
            self.container.set_children([])

        # Make a four-column layout
        number_views = [None] * _NUM_COLUMNS
        word_views = [None] * _NUM_COLUMNS

        words_per_page = len(self.words) // self.num_pages

        words_per_column = words_per_page // _NUM_COLUMNS
        word_idx = self.page_idx * words_per_page
        for col in range(_NUM_COLUMNS):
            number_views[col] = View(flex_flow=lv.FLEX_FLOW.COLUMN)

            number_views[col].set_size(20, lv.pct(100))
            number_views[col].set_no_scroll()
            with Stylize(number_views[col]) as default:
                # default.bg_color(BLUE, opa=64)
                if len(self.words) == 24:
                    default.pad_row(6)
                else:
                    default.pad_row(4)

            word_views[col] = View(flex_flow=lv.FLEX_FLOW.COLUMN)
            word_views[col].set_width(lv.SIZE.CONTENT)
            word_views[col].set_height(lv.pct(100))
            word_views[col].set_no_scroll()
            with Stylize(word_views[col]) as default:
                # default.bg_color(GREEN, opa=64)
                default.flex_fill()
                if len(self.words) == 24:
                    default.pad_row(6)
                else:
                    default.pad_row(4)

            for w in range(words_per_column):
                # Add the number
                number_view = Label(
                    text='{}'.format(recolor(HIGHLIGHT_TEXT_HEX, str(word_idx + 1))),
                    text_align=lv.TEXT_ALIGN.RIGHT)
                number_view.set_width(lv.pct(100))
                with Stylize(number_view) as default:
                    default.flex_fill()
                number_views[col].add_child(number_view)

                # Add the word
                word_view = Label(text=self.words[word_idx], color=TEXT_GREY)
                with Stylize(word_view) as default:
                    default.flex_fill()

                word_views[col].add_child(word_view)
                word_idx += 1

            # Add the columns
            self.container.add_child(number_views[col])
            self.container.add_child(word_views[col])

        if self.is_mounted():
            self.container.mount_children()

        # Update the page micron index
        common.ui.set_micron_bar_active_idx(self.page_idx)

        # Update microns
        if self.num_pages > 1:
            if self.page_idx == 0:
                common.ui.set_left_micron(None)
                common.ui.set_right_micron(microns.Forward)
            else:
                common.ui.set_left_micron(microns.Back)
                common.ui.set_right_micron(microns.Checkmark)
        else:
            common.ui.set_left_micron(None)
            common.ui.set_right_micron(microns.Checkmark)

    def attach(self, group):
        super().attach(group)
        group.add_obj(self.lvgl_root)

        # Add the page dots if necessary
        if self.num_pages > 1:
            micron_bar_card_descs = []
            for i in range(self.num_pages):
                micron_bar_card_descs.append({'page_micron': microns.PageDot})

            self.prev_card_idx = common.ui.active_card_idx
            self.prev_card_descs = common.ui.set_micron_bar_cards(micron_bar_card_descs, force_show=True)
            common.ui.set_micron_bar_active_idx(self.page_idx)

    def detach(self):
        if self.prev_card_descs is not None:
            common.ui.set_micron_bar_cards(self.prev_card_descs, force_show=False)
            common.ui.set_micron_bar_active_idx(self.prev_card_idx)
            self.prev_card_descs = None

        lv.group_remove_obj(self.lvgl_root)
        super().detach()

    def left_action(self, is_pressed):
        if not is_pressed:
            if self.page_idx > 0:
                # Go back a page
                self.page_idx -= 1
                self.update()

    def right_action(self, is_pressed):
        if not is_pressed:
            if self.page_idx == self.num_pages - 1:
                # At the last page, so we are showing Checkmark and can return
                self.set_result(True)
            elif self.page_idx < self.num_pages - 1:
                # Go forward a page
                self.page_idx += 1
                self.update()
