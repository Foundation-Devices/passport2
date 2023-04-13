# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# local_style.py

import lvgl as lv
from .font_sizes import *


class LocalStyle():
    def __init__(self, view, selector=0):
        self.view = view
        self.selector = selector
        self.lvgl_root = self.view.get_lvgl_root()
        self.props = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            import sys
            # print('with() exception: e={}'.format(exc_value))
            sys.print_exception(exc_value)
        return exc_type is not None

    def refresh(self, lvgl_obj):
        '''Remove all local styles and then reapply any styles in self.props.'''
        if self.view.is_mounted():
            # Iterate keys of self.props
            for prop in self.props.keys():
                value = self.props[prop]
                lvgl_obj.set_local_style_prop(prop, value)

    def set_prop(self, prop, value):
        if value is not None:
            self.props[prop] = value
            if self.view.is_mounted():
                lvgl_obj = self.view.get_lvgl_root()
                prop_func = getattr(lvgl_obj, 'set_style_' + prop)
                prop_func(value, self.selector)
        else:
            # Delete it so we don't apply it again later
            if lv.STYLE.BG_COLOR in self.props:
                del self.props[lv.STYLE.BG_COLOR]

            # TODO: But not sure if there is a way to remove this style from the active local style in LVGL
            # if self.view.is_mounted():
            #     lvgl_obj = self.view.get_lvgl_root()
            #     lvgl_obj.remove_local_style_prop(prop)

    def pad(self, top=None, right=None, bottom=None, left=None):
        if top is not None:
            self.set_prop('pad_top', top)
        if right is not None:
            self.set_prop('pad_right', right)
        if bottom is not None:
            self.set_prop('pad_bottom', bottom)
        if left is not None:
            self.set_prop('pad_left', left)

    def pad_all(self, value):
        self.pad(top=value, right=value, bottom=value, left=value)

    def no_pad(self):
        self.pad(top=0, right=0, bottom=0, left=0)

    def pad_row(self, value):
        self.set_prop('pad_row', value)

    def pad_col(self, value):
        self.set_prop('pad_column', value)

    def radius(self, value):
        self.set_prop('radius', value)

    def clip_corner(self, value):
        self.set_prop('clip_corner', value)

    def flex_flow(self, value):
        self.set_prop('flex_flow', value)
        self.set_prop('layout', lv.FLEX_FLEX.value)  # TODO: Shouldn't need the `.value` here

    def flex_fill(self):
        self.set_prop('flex_grow', 1)

    def flex_grow(self, value):
        self.set_prop('flex_grow', value)

    def flex_align(self, main=None, cross=None, track=None):
        if main is not None:
            self.set_prop('flex_main_place', main)
        if cross is not None:
            self.set_prop('flex_cross_place', cross)
        if track is not None:
            self.set_prop('flex_track_place', track)

    def align(self, align):
        self.set_prop('align', align)

    def outline(self, width=None, pad=None, opa=None, color=None):
        if width is not None:
            self.set_prop('outline_width', width)
        if pad is not None:
            self.set_prop('outline_pad', pad)
        if opa is not None:
            self.set_prop('outline_opa', opa)
        if color is not None:
            self.set_prop('outline_color', color)

    def copper_border(self):
        pass

    def no_border(self):
        self.border_width(0)

    def border_width(self, width):
        self.set_prop('border_width', width)

    def border_color(self, color):
        self.set_prop('border_color', color)

    def border_side(self, side):
        self.set_prop('border_side', side)

    def bg_color(self, color, opa=None):
        self.set_prop('bg_color', color)
        self.bg_opa(opa if opa is not None else 255)

    def bg_img(self, img_src, opa=None, tiled=False, recolor=None, recolor_opa=255):
        self.set_prop('bg_img_src', img_src)
        if opa is not None:
            self.set_prop('bg_opa', opa)
        if recolor is not None:
            self.set_prop('bg_img_recolor', recolor)
            self.set_prop('bg_img_recolor_opa', recolor_opa)
        self.set_prop('bg_img_tiled', tiled)

    def bg_transparent(self):
        self.bg_opa(0)

    def bg_opaque(self):
        self.bg_opa(255)

    def bg_opa(self, opa):
        self.set_prop('bg_opa', opa)

    def bg_blend_mode(self, mode):
        self.set_prop('bg_blend_mode', mode)

    def blend_mode(self, mode):
        self.set_prop('blend_mode', mode)

    def opa(self, opa):
        self.set_prop('opa', opa)

    def opa_scale(self, opa_scale):
        self.set_prop('opa_scale', opa_scale)

    def font(self, font=FONT_NORMAL):
        if font == FONT_TITLE:
            self.set_prop('text_font', lv.font_montserrat_22)
        elif font == FONT_NORMAL:
            self.set_prop('text_font', lv.font_montserrat_16)
        elif font == FONT_SMALL:
            self.set_prop('text_font', lv.font_montserrat_16)

    def text_color(self, color):
        self.set_prop('text_color', color)

    def text_align(self, align):
        self.set_prop('text_align', align)

    def img_recolor(self, color, opa=255):
        self.set_prop('img_recolor_opa', opa)
        self.set_prop('img_recolor', color)

    def img_recolor_opa(self, opa=255):
        self.set_prop('img_recolor_opa', opa)

    def bg_gradient(self, color1, color2, stop1=0, stop2=128, dir=lv.GRAD_DIR.VER):
        self.set_prop('bg_opa', lv.OPA.COVER)
        self.set_prop('bg_color', color1)
        self.set_prop('bg_grad_color', color2)
        self.set_prop('bg_grad_dir', dir)
        self.set_prop('bg_main_stop', stop1)
        self.set_prop('bg_grad_stop', stop2)

    def line_color(self, color):
        self.set_prop('line_color', color)

    def line_opa(self, opa):
        self.set_prop('line_opa', opa)

    def line_width(self, width):
        self.set_prop('line_width', width)
