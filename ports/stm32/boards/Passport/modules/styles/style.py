# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# __init__.py

import lvgl as lv
import common
import passport
from .font_sizes import *


class Stylize():
    '''Helper class to make creating and adding styles to Views easier and cleaner looking.'''

    def __init__(self, view, selector=0):
        self.view = view
        self.selector = selector
        self.style = Style(selector)

    def __enter__(self):
        return self.style

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            import sys
            # print('with() exception: e={}'.format(exc_value))
            sys.print_exception(exc_value)

        self.view.add_style(self.style)
        return exc_type is not None


def Style(selector=0):
    if passport.IS_COLOR:
        if common.is_dark_theme:
            return ColorDarkTheme(selector=selector)
        else:
            return ColorLightTheme(selector=selector)
    else:  # mono
        if common.is_dark_theme:
            return MonoDarkTheme(selector=selector)
        else:
            return MonoLightTheme(selector=selector)


class FoundationBaseTheme():
    def __init__(self, selector=0):
        self.selector = selector
        self.style = lv.style_t()
        self.style.init()

    def apply(self, lvgl_widget):
        lvgl_style_copy = self.style  # TODO: copy(self.style)
        lvgl_widget.add_style(lvgl_style_copy, self.selector)

    def pad(self, top=None, right=None, bottom=None, left=None):
        if top is not None:
            self.style.set_pad_top(top)
        if right is not None:
            self.style.set_pad_right(right)
        if bottom is not None:
            self.style.set_pad_bottom(bottom)
        if left is not None:
            self.style.set_pad_left(left)

    def pad_all(self, pad):
        self.style.set_pad_all(pad)

    def no_pad(self):
        self.pad_all(0)

    def pad_row(self, pad):
        self.style.set_pad_row(pad)

    def pad_col(self, pad):
        self.style.set_pad_column(pad)

    def radius(self, r):
        self.style.set_radius(r)

    def clip_corner(self, clip):
        self.style.set_clip_corner(clip)

    def flex_flow(self, direction):
        self.style.set_flex_flow(direction)
        self.style.set_layout(lv.LAYOUT_FLEX.value)  # TODO: Shouldn't need the `.value` here

    def flex_fill(self):
        self.style.set_flex_grow(1)

    def flex_grow(self, flex_grow):
        self.style.set_flex_grow(flex_grow)

    def flex_align(self, main=None, cross=None, track=None):
        if main is not None:
            self.style.set_flex_main_place(main)
        if cross is not None:
            self.style.set_flex_cross_place(cross)
        if track is not None:
            self.style.set_flex_track_place(track)

    def align(self, align):
        self.style.set_align(align)

    def outline(self, width=None, pad=None, opa=None, color=None):
        if width is not None:
            self.style.set_outline_width(width)
        if pad is not None:
            self.style.set_outline_pad(pad)
        if opa is not None:
            self.style.set_outline_opa(opa)
        if color is not None:
            self.style.set_outline_color(color)

    def copper_border(self):
        pass

    def no_border(self):
        self.border_width(0)

    def border_width(self, width):
        self.style.set_border_width(width)

    def border_color(self, color):
        self.style.set_border_color(color)

    def border_side(self, side):
        self.style.set_border_side(side)

    def bg_color(self, color, opa=None):
        self.style.set_bg_color(color)
        self.bg_opa(opa if opa is not None else 255)

    def bg_img(self, img_src, opa=None, tiled=False, recolor=None, recolor_opa=255):
        self.style.set_bg_img_src(img_src)
        if opa is not None:
            self.style.set_bg_img_opa(opa)
        if recolor is not None:
            self.style.set_bg_img_recolor(recolor)
            self.style.set_bg_img_recolor_opa(recolor_opa)
        self.style.set_bg_img_tiled(tiled)

    def bg_transparent(self):
        self.style.set_bg_opa(0)

    def bg_opaque(self):
        self.style.set_bg_opa(255)

    def bg_opa(self, opa):
        self.style.set_bg_opa(opa)

    def bg_blend_mode(self, mode):
        self.style.set_bg_blend_mode(mode)

    def blend_mode(self, mode):
        self.style.set_blend_mode(mode)

    def opa(self, opa):
        self.style.set_opa(opa)

    def opa_scale(self, opa_scale):
        self.style.set_opa_scale(opa_scale)

    def font(self, font=FONT_NORMAL):
        if passport.IS_COLOR:
            self.style.set_text_font(lv.font_montserrat_16)
        else:
            self.style.set_text_font(lv.font_montserrat_16_mono)

    def text_color(self, color):
        self.style.set_text_color(color)

    def text_align(self, align):
        self.style.set_text_align(align)

    def img_recolor(self, color, opa=255):
        self.style.set_img_recolor_opa(opa)
        self.style.set_img_recolor(color)

    def img_recolor_opa(self, opa=255):
        self.style.set_img_recolor_opa(opa)

    def bg_gradient(self, color1, color2, stop1=0, stop2=128, dir=lv.GRAD_DIR.VER):
        self.style.set_bg_opa(lv.OPA.COVER)
        self.style.set_bg_color(color1)
        self.style.set_bg_grad_color(color2)
        self.style.set_bg_grad_dir(dir)
        self.style.set_bg_main_stop(stop1)
        self.style.set_bg_grad_stop(stop2)

    def line_color(self, color):
        self.style.set_line_color(color)

    def line_opa(self, opa):
        self.style.set_line_opa(opa)

    def line_width(self, width):
        self.style.set_line_width(width)

    def anim_time(self, time):
        self.style.set_anim_time(time)


class ColorDarkTheme(FoundationBaseTheme):
    def __init__(self, selector=0):
        super().__init__(selector=selector)


class ColorLightTheme(FoundationBaseTheme):
    def __init__(self, selector=0):
        super().__init__(selector=selector)


class MonoDarkTheme(FoundationBaseTheme):
    def __init__(self, selector=0):
        super().__init__(selector=selector)


class MonoLightTheme(FoundationBaseTheme):
    def __init__(self, selector=0):
        super().__init__(selector=selector)
