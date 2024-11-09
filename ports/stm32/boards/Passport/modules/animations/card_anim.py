# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# card_anim.py

import lvgl as lv
import common
from .prop_cb import anim_obj_prop, anim_x_cb
from .constants import DEFAULT_ANIM_SPEED


def push_card(curr_card_widget, curr_x, new_card_widget, done_cb=None, duration_ms=DEFAULT_ANIM_SPEED):
    num_cbs = 0

    def counter_cb(_anim):
        nonlocal num_cbs
        num_cbs += 1
        if num_cbs >= 2 and done_cb is not None:
            done_cb()

    x = curr_card_widget.get_x()

    anim_obj_prop(curr_card_widget, curr_x, -common.display.WIDTH,
                  anim_x_cb, done_cb=counter_cb, duration_ms=duration_ms)

    anim_obj_prop(new_card_widget, common.display.WIDTH, curr_x,
                  anim_x_cb, done_cb=counter_cb, duration_ms=duration_ms)


def pop_card(curr_card_widget, curr_x, new_card_widget, done_cb=None, duration_ms=DEFAULT_ANIM_SPEED):
    num_cbs = 0

    def counter_cb(_anim):
        nonlocal num_cbs
        num_cbs += 1
        if num_cbs >= 2 and done_cb is not None:
            done_cb()

    anim_obj_prop(curr_card_widget, curr_x, common.display.WIDTH,
                  anim_x_cb, done_cb=counter_cb, duration_ms=duration_ms)

    anim_obj_prop(new_card_widget, -common.display.WIDTH, curr_x,
                  anim_x_cb, done_cb=counter_cb, duration_ms=duration_ms)
