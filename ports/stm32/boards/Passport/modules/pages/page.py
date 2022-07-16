# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# page.py

from animations.constants import TRANSITION_DIR_POP, TRANSITION_DIR_PUSH
import lvgl as lv
from utils import handle_fatal_error
from views import View
from uasyncio import sleep_ms
from styles import Stylize
import common


class Page(View):
    def __init__(self, card_header=None, statusbar=None, left_micron=None, right_micron=None,
                 flex_flow=lv.FLEX_FLOW.COLUMN):
        super().__init__(flex_flow=flex_flow)

        self.card_header = card_header
        self.prev_card_header = None
        self.statusbar = statusbar
        self.prev_statusbar = None
        self.left_micron = left_micron
        self.right_micron = right_micron

        self.done = False
        self.result = None
        self.auto_close_timer = None

        self.set_width(lv.pct(100))
        with Stylize(self) as default:
            default.flex_fill()

    def mount(self, lvgl_parent):
        super().mount(lvgl_parent)
        common.ui.set_left_micron(self.left_micron)
        common.ui.set_right_micron(self.right_micron)

    def unmount(self):
        super().unmount()

    def attach(self, group):
        common.keypad.set_active_page(self)

        super().attach(group)

    def detach(self):
        super().detach()
        common.keypad.set_active_page(None)

    def left_action(self, is_pressed):
        # print('Page.right_action()')
        if not is_pressed:
            self.set_result(False)

    def right_action(self, is_pressed):
        # print('Page.right_action()')
        if not is_pressed:
            self.set_result(True)

    # By default, returns None so caller can differentiate between user pressing a button to back out
    # vs. backing out due to the timeout.
    #
    # Pages can override this if they need to set a different result.
    def on_auto_close(self, timer):
        if self.auto_close_timer is not None:
            self.auto_close_timer._del()
            self.auto_close_timer = None
            # print('Set result to None')
            self.set_result(None)

    async def show(self, auto_close_timeout=None):
        from common import ui
        done = False
        if ui.get_active_page() is None:
            ui.set_page(self)
        elif common.page_transition_dir == TRANSITION_DIR_PUSH:
            ui.push_page(self)
        elif common.page_transition_dir == TRANSITION_DIR_POP:
            ui.pop_page(self)
        else:  # TRANSITION_DIR_REPLACE
            ui.set_page(self)

        self.result = None
        self.done = False

        # Setup timer for auto-close if requested
        if auto_close_timeout is not None:
            self.auto_close_timer = lv.timer_create(self.on_auto_close, auto_close_timeout, None)
        else:
            self.auto_close_timer = None

        # Set the custom card title if caller gave one
        if self.card_header is not None:
            self.prev_card_header = common.ui.set_card_header(**self.card_header)

        if self.statusbar is not None:
            self.prev_statusbar = common.ui.set_statusbar(**self.statusbar)

        g = self.poll_for_done()
        while not done:
            try:
                next(g)
                await sleep_ms(10)
            except StopIteration as result:
                # The result is of type StopIteration, so we need to reach in and get the actual value

                # Restore statusbar if we overrode it
                if self.prev_statusbar is not None:
                    common.ui.set_statusbar(**self.prev_statusbar)

                # Restore card title if we overrode it
                if self.prev_card_header is not None:
                    common.ui.set_card_header(**self.prev_card_header, force_all=True)

                return result.value
            except Exception as e:
                handle_fatal_error(e)

    def poll_for_done(self):
        while not self.done:
            yield None
        return self.result

    def set_result(self, result):
        # print('Page.set_result({})'.format(result))
        self.result = result
        self.done = True

    def back(self):
        # print('Page.back()')
        self.done = True
        self.result = None
