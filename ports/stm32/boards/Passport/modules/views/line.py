# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# line.py - Simple wrapper around a line widget

import lvgl as lv
from styles import Stylize
from styles.colors import WHITE
from views import View


class Line(View):
    def __init__(self, points, color=WHITE, width=1):
        super().__init__()
        self.points = points
        self.color = color
        self.line_width = width

        # TODO: Perhaps move this to a local style in mount() so we don't have two styles all the time
        with Stylize(self) as default:
            default.line_color(self.color)
            default.line_width(self.line_width)

    def set_points(self, points):
        self.points = points
        if self.is_mounted():
            self.lvgl_root.set_points(self.points)

    def create_lvgl_root(self, lvgl_parent):
        return lv.line(lvgl_parent)

    def mount(self, lvgl_parent):
        super().mount(lvgl_parent)
        self.lvgl_root.set_points(self.points, len(self.points))
        return self.lvgl_root
