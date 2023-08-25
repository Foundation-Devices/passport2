# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# main_screen.py - Main screen that shows the recolorable background image, and contains
#                  the StatusBar and CardNav components.

import lvgl as lv
from styles.colors import CARD_BG_GREY, BLACK
from views import View
import passport
import common


class MainScreen(View):
    def __init__(self):
        import lvgl as lv
        from views import StatusBar, CardNav
        from styles import Stylize
        from display import Display

        super().__init__()
        self.set_pos(0, 0)
        self.set_size(lv.pct(100), lv.pct(100))
        self.set_no_scroll()

        self.bg_color = BLACK
        with Stylize(self) as default:
            default.bg_color(self.bg_color)

        w = Display.WIDTH
        h = Display.HEIGHT

        # BG Container
        self.bg_container = View()
        self.bg_container.set_pos(1, 1)
        self.bg_container.set_size(w - 2, h - 2)
        with Stylize(self.bg_container) as default:
            default.radius(8)

        # Overlay texture
        self.overlay = View()
        self.overlay.set_pos(1, 1)
        self.overlay.set_size(w - 2, h - 2)

        # The overlay doesn't change, so just set it once here
        with Stylize(self.overlay) as default:
            if passport.IS_COLOR:
                default.bg_img(lv.IMAGE_SCREEN_OVERLAY)
            else:
                default.bg_img(lv.IMAGE_SCREEN_OVERLAY_6)
            default.radius(8)

        # Main content container
        self.main_container = View(flex_flow=lv.FLEX_FLOW.COLUMN)
        self.main_container.set_pos(0, 0)
        self.main_container.set_size(w, h)

        with Stylize(self.main_container) as default:
            default.pad_row(0)

        self.update_background()

        self.statusbar = StatusBar()

        self.card_nav = CardNav()

        with Stylize(self.card_nav) as default:
            default.flex_fill()

        self.main_container.set_children([self.statusbar, self.card_nav])

        self.set_children([self.bg_container, self.overlay, self.main_container])

    def update_background(self):
        from styles.local_style import LocalStyle

        if passport.IS_COLOR:
            # Update the gradient only for the color screen
            with LocalStyle(self.bg_container) as style:
                style.bg_gradient(self.bg_color, CARD_BG_GREY, stop1=20, stop2=192)
        else:
            NUM_ACCOUNT_TEXTURES = 6

            # Mono screen backgrounds use texture instead of color
            acct = None
            if common.ui is not None:
                acct = common.ui.get_active_account()

            if acct is not None:
                idx = acct.get('acct_num') % NUM_ACCOUNT_TEXTURES
            else:
                # There is a final texture for other screens
                idx = NUM_ACCOUNT_TEXTURES

            overlay_name = 'IMAGE_SCREEN_OVERLAY_{}'.format(idx)
            # print('overlay_name={}'.format(overlay_name))
            with LocalStyle(self.overlay) as default:
                default.bg_img(getattr(lv, overlay_name))
                default.radius(8)

            # Mono screen backgrounds use texture instead of color
            acct = None
            if common.ui is not None:
                acct = common.ui.get_active_account()

            if acct is not None:
                idx = acct.get('acct_num') % NUM_ACCOUNT_TEXTURES
            else:
                # There is a final texture for other screens
                idx = NUM_ACCOUNT_TEXTURES

            overlay_name = 'IMAGE_SCREEN_OVERLAY_{}'.format(idx)
            # print('overlay_name={}'.format(overlay_name))
            with LocalStyle(self.overlay) as default:
                default.bg_img(getattr(lv, overlay_name))
                default.radius(8)

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
