# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# container.py - Default widget with some LVGL styles applied.  Used mainly as the root container for View subclasses.

import lvgl as lv


def Container(lvgl_parent=None, flex_flow=None):
    from styles import Style

    container = lv.obj(lvgl_parent)
    default = Style()
    default.bg_transparent()
    default.no_border()
    default.no_pad()
    default.radius(0)
    if flex_flow is not None:
        default.flex_flow(flex_flow)

    default.apply(container)

    return container
