# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# filler.py - A transparent container that fills in space in a flex layout

import lvgl as lv
from styles import Stylize
from views import View


class Filler(View):
    def __init__(self, flex_grow=1):
        super().__init__()

        with Stylize(self) as default:
            default.flex_grow(self.flex_grow)

        self.set_width(lv.SIZE.CONTENT)
        self.set_height(lv.SIZE.CONTENT)
