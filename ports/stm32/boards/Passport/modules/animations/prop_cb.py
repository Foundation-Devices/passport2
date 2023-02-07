# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# prop_cb.py

import lvgl as lv
from .constants import DEFAULT_ANIM_SPEED


def anim_obj_prop(widget, start, end, prop_exec_cb, done_cb=None, duration_ms=DEFAULT_ANIM_SPEED):
    anim = lv.anim_t()
    anim.init()
    anim.set_var(widget)
    anim.set_values(start, end)
    anim.set_time(duration_ms)
    anim.set_path_cb(lv.anim_t.path_linear)
    anim.set_custom_exec_cb(lambda _anim, value: prop_exec_cb(widget, value))

    if done_cb is not None:
        anim.set_ready_cb(done_cb)
    lv.anim_t.start(anim)


def anim_x_cb(widget, value):
    # print('widget={} value={}'.format(widget, value))
    widget.set_x(value)


def anim_y_cb(widget, value):
    widget.set_y(value)


def anim_opa_cb(widget, value):
    widget.set_style_opa(value, 0)
