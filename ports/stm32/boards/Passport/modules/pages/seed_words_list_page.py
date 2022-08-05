# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# account_details_page.py - Show a page with information for the current account.

import lvgl as lv
from pages import Page
from styles.style import Stylize
from views import View, Label
import microns
from styles.colors import FD_BLUE_HEX, TEXT_GREY

NUM_COLUMNS = 2


class SeedWordsListPage(Page):
    def __init__(
            self,
            words=[],
            card_header=None,
            statusbar=None,
            left_micron=microns.Back,
            right_micron=microns.Checkmark):
        from utils import recolor

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

        self.container.set_height(lv.SIZE.CONTENT)
        with Stylize(self.container) as default:
            if len(words) == 24:
                default.pad(top=8, bottom=8)
            else:
                default.align(lv.ALIGN.CENTER)
            default.pad_col(4)

        with Stylize(self, selector=lv.PART.SCROLLBAR) as scrollbar:
            scrollbar.pad(right=0)

        # Make a four-column layout
        num_views = [None] * NUM_COLUMNS
        word_views = [None] * NUM_COLUMNS

        words_per_column = len(words) // NUM_COLUMNS
        word_idx = 0
        for col in range(NUM_COLUMNS):
            print('col={}'.format(col))
            num_views[col] = View(flex_flow=lv.FLEX_FLOW.COLUMN)
            num_views[col].set_size(20, lv.SIZE.CONTENT)
            num_views[col].set_no_scroll()
            with Stylize(num_views[col]) as default:
                if len(words) == 24:
                    default.pad_row(6)
                else:
                    default.pad_row(4)

            word_views[col] = View(flex_flow=lv.FLEX_FLOW.COLUMN)
            word_views[col].set_width(lv.SIZE.CONTENT)
            word_views[col].set_height(lv.SIZE.CONTENT)
            num_views[col].set_no_scroll()
            with Stylize(word_views[col]) as default:
                if len(words) == 24:
                    default.pad_row(6)
                else:
                    default.pad_row(4)

            for w in range(words_per_column):
                # Add the number
                num_view = Label(
                    text='{}'.format(recolor(FD_BLUE_HEX, str(word_idx + 1))),
                    text_align=lv.TEXT_ALIGN.RIGHT)
                num_view.set_width(lv.pct(100))
                num_views[col].add_child(num_view)

                # Add the word
                word_view = Label(text=words[word_idx], color=TEXT_GREY)
                word_views[col].add_child(word_view)
                word_idx += 1

            # Add the columns
            self.container.add_child(num_views[col])
            self.container.add_child(word_views[col])

    def attach(self, group):
        super().attach(group)
        group.add_obj(self.lvgl_root)

    def detach(self):
        lv.group_remove_obj(self.lvgl_root)
        super().detach()
