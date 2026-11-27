# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# image.py - A simple, recolorable image component

import lvgl as lv
from styles import Stylize, LocalStyle
from views import View


class Image(View):
    def __init__(self, src, color=None, opa=None):
        super().__init__()
        self.src = src
        self.color = color
        self.opa = opa

        with Stylize(self) as default:
            if self.color is not None:
                default.img_recolor(self.color)
            if self.opa is not None:
                default.opa(self.opa)

    def set_src(self, src):
        self.src = src
        self.update()

    def create_lvgl_root(self, lvgl_parent):
        root = lv.img(lvgl_parent)
        root.set_src(self.src)
        return root

    def update(self):
        if self.is_mounted():
            self.lvgl_root.set_src(self.src)

        with LocalStyle(self) as style:
            if self.color is not None:
                style.img_recolor(self.color)
            if self.opa is not None:
                style.img_recolor_opa(self.opa)
