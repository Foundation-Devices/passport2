# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# page_anim.py

import lvgl as lv
from micropython import const
from .prop_cb import anim_obj_prop, anim_x_cb, anim_opa_cb
from .constants import DEFAULT_ANIM_SPEED

ANIM_MOVE_DISTANCE = const(100)


def push_page(old_page_widget, new_page_widget, done_cb=None, duration_ms=DEFAULT_ANIM_SPEED):
    num_anims = 0
    num_cbs = 0

    # duration_ms = 0

    def counter_cb(_anim):
        nonlocal num_cbs
        num_cbs += 1
        if num_cbs >= num_anims:
            done_cb()

    if old_page_widget is not None:
        anim_obj_prop(old_page_widget, 0, -ANIM_MOVE_DISTANCE, anim_x_cb, duration_ms=duration_ms, done_cb=counter_cb)
        anim_obj_prop(old_page_widget, 255, 0, anim_opa_cb, duration_ms=duration_ms, done_cb=counter_cb)
        num_anims += 2

    anim_obj_prop(new_page_widget, ANIM_MOVE_DISTANCE, 0, anim_x_cb, duration_ms=duration_ms, done_cb=counter_cb)
    anim_obj_prop(new_page_widget, 0, 255, anim_opa_cb, duration_ms=duration_ms, done_cb=counter_cb)
    num_anims += 2


def pop_page(old_page_widget, new_page_widget, done_cb=None, duration_ms=DEFAULT_ANIM_SPEED):
    num_anims = 0
    num_cbs = 0

    # duration_ms = 0

    def counter_cb(_anim):
        nonlocal num_cbs
        num_cbs += 1
        if num_cbs >= num_anims:
            done_cb()

    if old_page_widget is not None:
        anim_obj_prop(old_page_widget, 0, ANIM_MOVE_DISTANCE, anim_x_cb, duration_ms=duration_ms, done_cb=counter_cb)
        anim_obj_prop(old_page_widget, 255, 0, anim_opa_cb, duration_ms=duration_ms, done_cb=counter_cb)
        num_anims += 2

    anim_obj_prop(new_page_widget, -ANIM_MOVE_DISTANCE, 0, anim_x_cb, duration_ms=duration_ms, done_cb=counter_cb)
    anim_obj_prop(new_page_widget, 0, 255, anim_opa_cb, duration_ms=duration_ms, done_cb=counter_cb)
    num_anims += 2
