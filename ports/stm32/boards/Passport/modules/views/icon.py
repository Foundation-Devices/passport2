# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# icon.py - A recolorable icon view

import lvgl as lv
from styles import Stylize, LocalStyle
from views import View


class Icon(View):
    def __init__(self, icon, color=None, opa=None):
        from utils import derive_icon

        super().__init__()
        self.icon = derive_icon(icon)
        self.color = color
        self.opa = opa

        with Stylize(self) as default:
            if self.color is not None:
                default.img_recolor(self.color)
            if self.opa is not None:
                default.opa(self.opa)

    def set_icon(self, icon):
        from utils import derive_icon

        self.icon = derive_icon(icon)
        self.update()

    def set_color(self, color=None, opa=None):
        if color is not None:
            self.color = color
        if opa is not None:
            self.opa = opa

        self.update()

    def create_lvgl_root(self, lvgl_parent):
        root = lv.img(lvgl_parent)
        root.set_src(self.icon)
        return root

    def update(self):
        if self.is_mounted():
            self.lvgl_root.set_src(self.icon)

        # TODO: This is not working!
        with LocalStyle(self) as style:
            if self.opa is not None:
                style.img_recolor_opa(self.opa)
            if self.color is not None:
                style.img_recolor(self.color)
