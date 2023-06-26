# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# card.py - Card header and card content - Custom content and header title and icon can be passed in

import lvgl as lv
from styles.colors import (LIGHT_GREY, MEDIUM_GREY, CARD_HEADER_TEXT, WHITE)
from styles import Stylize, LocalStyle
from views import View, Image, Label
import microns
from animations import page_anim
import passport
from constants import (CARD_CONTENT_HEIGHT_WITHOUT_HEADER, CARD_HEADER_HEIGHT,
                       CARD_BORDER_WIDTH, OUTER_CORNER_RADIUS, CARD_OUTER_MONO_BORDER_WIDTH)


class Card(View):

    def __init__(
            self,
            title=None,
            icon=None,
            right_icon=None,
            page_micron=None,
            right_text=None,
            initial_page=None,
            bg_color=MEDIUM_GREY,
            header_color=LIGHT_GREY,
            header_fg_color=CARD_HEADER_TEXT):
        super().__init__()

        self.title = title
        self.icon = icon
        self.right_icon = right_icon
        self.page_micron = page_micron if page_micron is not None else microns.PageDot()
        self.right_text = right_text
        self.page = initial_page

        # Some colors that the MainScreen can use for differentiating the background
        self.bg_color = bg_color
        self.header_color = header_color
        self.header_fg_color = header_fg_color

        self.header = None
        self._hide_header = False  # Whether to override the visibility of the header
        self.chevron_height = lv.IMAGE_CARD_BOTTOM.header.h

        # Background container
        self.bg_container = View()
        self.bg_container.set_size(lv.pct(100), lv.pct(100))
        self.bg_container.set_no_scroll()
        with Stylize(self.bg_container) as default:
            default.align(lv.ALIGN.TOP_MID)
            default.pad_row(0)
        self.add_child(self.bg_container)

        border_radius = OUTER_CORNER_RADIUS
        # Need an extra outer border for the mono screen
        if passport.IS_COLOR:
            container = self.bg_container
        else:
            border_radius = OUTER_CORNER_RADIUS + 4
            self.card_border_outer = View()
            self.card_border_outer.set_size(lv.pct(100), lv.pct(94))
            with Stylize(self.card_border_outer) as default:
                default.pad(top=CARD_OUTER_MONO_BORDER_WIDTH,
                            left=CARD_OUTER_MONO_BORDER_WIDTH, right=CARD_OUTER_MONO_BORDER_WIDTH)
                default.radius(border_radius)
                default.bg_color(WHITE)
            border_radius -= CARD_OUTER_MONO_BORDER_WIDTH
            self.bg_container.add_child(self.card_border_outer)
            container = self.card_border_outer

        self.card_border = View()
        if passport.IS_COLOR:
            self.card_border.set_size(lv.pct(100), lv.pct(94))
        else:
            self.card_border.set_size(lv.pct(100), lv.pct(100))
        with Stylize(self.card_border) as default:
            default.pad(left=CARD_BORDER_WIDTH, right=CARD_BORDER_WIDTH)
            default.radius(border_radius)
        border_radius -= CARD_BORDER_WIDTH

        container.add_child(self.card_border)

        self.card_fill = View()
        self.card_fill.set_size(lv.pct(100), lv.pct(100))
        with Stylize(self.card_fill) as default:
            default.bg_color(WHITE)
            default.radius(border_radius)
        self.card_border.add_child(self.card_fill)

        # Bottom chevron
        self.chevron_image = Image(lv.IMAGE_CARD_BOTTOM)
        with Stylize(self.chevron_image) as default:
            default.align(lv.ALIGN.BOTTOM_MID)
        self.bg_container.add_child(self.chevron_image)

        # # Foreground container - holds the header text and icon, followed by the actual content
        self.fg_container = View(flex_flow=lv.FLEX_FLOW.COLUMN)
        self.fg_container.set_width(lv.pct(100))
        self.fg_container.set_height(CARD_CONTENT_HEIGHT_WITHOUT_HEADER)
        self.fg_container.set_no_scroll()
        with Stylize(self.fg_container) as default:
            if passport.IS_COLOR:
                default.pad(left=CARD_BORDER_WIDTH * 2, right=CARD_BORDER_WIDTH * 2)
            else:
                default.pad(left=CARD_BORDER_WIDTH * 2 + CARD_OUTER_MONO_BORDER_WIDTH,
                            right=CARD_BORDER_WIDTH * 2 + CARD_OUTER_MONO_BORDER_WIDTH)
            default.radius(border_radius)
        self.add_child(self.fg_container)

        # Page container (no flex layout so animations work)
        self.page_container = View()
        self.page_container.set_width(lv.pct(100))
        self.page_container.set_no_scroll()
        with Stylize(self.page_container) as default:
            default.flex_fill()

        # Page content
        if self.page is not None:
            self.page_container.set_children([self.page])

        self.fg_container.add_child(self.page_container)

        self.update()

    def is_header_visible(self):
        return self.title is not None and not self._hide_header

    def show_header(self):
        self._hide_header = False
        # self.update_header_bg()
        self.update_header()
        self.update_fg_container()

    def hide_header(self):
        self._hide_header = True
        # self.update_header_bg()
        self.update_header()
        self.update_fg_container()

    def get_header(self):
        return {
            'title': self.title,
            'icon': self.icon,
            'right_icon': self.right_icon,
            'right_text': self.right_text,
            'bg_color': self.header_color,
            'fg_color': self.header_fg_color
        }

    def set_header(self,
                   title=None,
                   icon=None,
                   right_icon=None,
                   right_text=None,
                   bg_color=None,
                   fg_color=None,
                   force_all=True):
        self.title = title

        if icon is not None or force_all:
            self.icon = icon

        if right_icon is not None or force_all:
            self.right_icon = right_icon

        if right_text is not None or force_all:
            self.right_text = right_text

        if bg_color is not None or force_all:
            self.header_color = bg_color
            # self.update_header_bg()

        if fg_color is not None or force_all:
            self.header_fg_color = fg_color

        self.update()

    def update(self):
        from utils import derive_icon

        # Always update the color and top padding
        top_pad = CARD_HEADER_HEIGHT if self.is_header_visible() else CARD_BORDER_WIDTH
        with LocalStyle(self.card_border) as style:
            style.bg_gradient(self.header_color, LIGHT_GREY)
            style.pad(top=top_pad)

        if self.is_mounted() and self.header is not None and self.header.is_mounted():
            self.header.unmount()
            del self.fg_container.children[0]

        # Header is only present if there is a title provided
        if self.is_header_visible():
            self.header = View()
            self.header.set_size(lv.pct(100), CARD_HEADER_HEIGHT)

            with Stylize(self.header) as default:
                default.pad(left=CARD_BORDER_WIDTH, right=CARD_BORDER_WIDTH)
                # default.bg_color(GREEN, 128)

            if self.icon is not None:
                icon = derive_icon(self.icon)
                self.icon_view = Image(icon, color=self.header_fg_color)
                with Stylize(self.icon_view) as default:
                    default.align(lv.ALIGN.LEFT_MID)
                self.header.add_child(self.icon_view)

            header_title = Label(text=self.title, color=self.header_fg_color, long_mode=lv.label.LONG.SCROLL_CIRCULAR)
            header_title.set_width(lv.pct(80))
            with Stylize(header_title) as default:
                default.text_align(lv.TEXT_ALIGN.CENTER)
                default.align(lv.ALIGN.CENTER)
            self.header.add_child(header_title)

            if self.right_icon is not None:
                right_icon = derive_icon(self.right_icon)
                self.right_icon_view = Image(right_icon, color=self.header_fg_color)
                with Stylize(self.right_icon_view) as default:
                    default.align(lv.ALIGN.RIGHT_MID)
                self.header.add_child(self.right_icon_view)

            # Only draw right text if there is no right icon
            if self.right_text is not None and self.right_icon is None:
                right_text_view = Label(text=self.right_text, color=self.header_fg_color)
                with Stylize(right_text_view) as default:
                    default.text_align(lv.TEXT_ALIGN.CENTER)
                    default.align(lv.ALIGN.RIGHT_MID)
                self.header.add_child(right_text_view)

            self.fg_container.insert_child(0, self.header)

            if self.is_mounted():
                self.header.mount(self.fg_container.lvgl_root)
                self.header.lvgl_root.move_to_index(0)

        # fg_container styles
        if self.is_header_visible():
            with LocalStyle(self.fg_container) as style:
                if passport.IS_COLOR:
                    style.pad(top=0)
                else:
                    style.pad(top=CARD_OUTER_MONO_BORDER_WIDTH)
                style.pad_row(CARD_BORDER_WIDTH)
        else:
            with LocalStyle(self.fg_container) as style:
                if passport.IS_COLOR:
                    style.pad(top=CARD_BORDER_WIDTH * 2)
                else:
                    style.pad(top=CARD_BORDER_WIDTH * 2 + CARD_OUTER_MONO_BORDER_WIDTH)
                style.pad_row(0)

    def attach(self, group):
        super().attach(group)
        if self.page is not None:
            self.page.attach(group)

    def detach(self):
        if self.page is not None:
            self.page.detach()
        super().detach()

    # TODO: Refactor code below so the common code is in a function

    # Mount and animate the given page so it replaces the current page with a "push" style.
    # The animation starts with the new page slightly to the right of the final position with alpha 0,
    # then animates the alpha to 255.
    # At the same time, it animates the position of the current page from center to slightly to the left,
    # while fading alpha from 255 to 0.
    # Timing and distance to move are configurable for each animation.
    # If there is no active page, just
    def push_page(self, new_page):
        from common import keypad, display

        keypad.set_is_animating(True)
        group = self.group
        old_page = self.page
        if old_page is not None:
            old_page.detach()

        def done_cb():
            self.page = new_page

            if old_page is not None:
                old_page.unmount()

            if group is not None:
                new_page.attach(group)

            keypad.set_is_animating(False)

        # Set the new page offscreen to start with
        new_page.set_x(0)
        new_page.set_size(lv.pct(100), lv.pct(100))

        new_page.mount(self.page_container.lvgl_root)

        self.update()

        page_anim.push_page(old_page.lvgl_root if old_page is not None else None, new_page.lvgl_root, done_cb=done_cb)

    def pop_page(self, new_page):
        from common import keypad, display

        keypad.set_is_animating(True)
        group = self.group
        old_page = self.page
        if old_page is not None:
            old_page.detach()

        def done_cb():
            self.page = new_page

            if old_page is not None:
                old_page.unmount()

            if group is not None:
                new_page.attach(group)

            # See if user hit any keys while we were animating
            keypad.set_is_animating(False)

        # Set the new page offscreen to start with
        new_page.set_x(0)
        new_page.set_size(lv.pct(100), lv.pct(100))

        new_page.mount(self.page_container.lvgl_root)

        self.update()

        page_anim.pop_page(old_page.lvgl_root if old_page is not None else None, new_page.lvgl_root, done_cb=done_cb)

    def set_page(self, new_page):
        import gc

        group = self.group
        old_page = self.page
        if old_page is not None:
            old_page.detach()
            old_page.unmount()

        gc.collect()

        # New page
        self.page = new_page
        new_page.set_size(lv.pct(100), lv.pct(100))
        new_page.mount(self.page_container.lvgl_root)
        if group is not None:
            new_page.attach(group)

        self.update()
