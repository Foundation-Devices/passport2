# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# main_screen.py - Main screen that shows the recolorable background image, and contains
#                  the StatusBar and CardNav components.

from views import View


class MainScreen(View):
    MARGIN_LEFT = 10
    MARGIN_RIGHT = 10
    MARGIN_TOP = 10
    MARGIN_BOTTOM = 10

    def __init__(self):
        import lvgl as lv
        from views import StatusBar, CardNav
        from styles import Stylize

        super().__init__()
        self.set_pos(0, 0)
        self.set_size(lv.pct(100), lv.pct(100))
        self.set_no_scroll()

        from styles.colors import BLACK
        self.bg_color = BLACK

        with Stylize(self) as default:
            default.bg_color(BLACK)

        # NOTE: The code below is a bit more complex as we draw a black border and rounded black corners on the
        #       screen to help avoid seeing the sharp screen corners under the rounded corners of the plastic
        #       front cover.
        # Split the background into two parts so we can use two gradients
        self.gradient = View()
        self.gradient.set_pos(1, 1)
        self.gradient.set_size(240 - 2, 320 - 2)

        # Diagonal lines background overlay
        self.right_container = View()
        # TODO: Make these calculated by screen height/width so they work for Gen 1 too
        self.right_container.set_pos(240 // 2, 1)
        self.right_container.set_size(240 // 2 - 1, 320 - 2)
        with Stylize(self.right_container) as default:
            default.bg_img(lv.IMAGE_DIAGONAL_LINES, tiled=True, opa=72)

        self.main_container = View(flex_flow=lv.FLEX_FLOW.COLUMN)
        with Stylize(self.main_container) as default:
            default.pad_row(0)
        self.main_container.set_pos(0, 0)
        self.main_container.set_size(lv.pct(100), lv.pct(100))

        self.update_background()

        self.statusbar = StatusBar()

        self.card_nav = CardNav()

        with Stylize(self.card_nav) as default:
            default.flex_fill()

        self.main_container.set_children([self.statusbar, self.card_nav])

        self.set_children([self.gradient, self.right_container, self.main_container])

    def update_background(self):
        import lvgl as lv
        from styles.local_style import LocalStyle

        # Apply a style for the background gradient
        with LocalStyle(self.gradient) as style:
            style.bg_gradient(self.bg_color, lv.color_hex(0xF7F7F7), stop1=10, stop2=192)
            style.radius(8)

    def get_title(self):
        return self.statusbar.title

    def get_icon(self):
        return self.statusbar.context_icon

    def set_statusbar(self, title=None, icon=None, fg_color=None):
        prev_title = self.statusbar.title
        prev_icon = self.statusbar.icon
        prev_fg_color = self.statusbar.fg_color

        if title is not None:
            self.statusbar.set_title(title)

        if icon is not None:
            self.statusbar.set_icon(icon)

        if fg_color is not None:
            self.statusbar.set_fg_color(fg_color)

        return {'title': prev_title, 'icon': prev_icon, 'fg_color': prev_fg_color}

    def set_bg_color(self, bg_color):
        self.bg_color = bg_color
        self.update_background()

    def attach(self, group):
        super().attach(group)
        self.card_nav.attach(group)
