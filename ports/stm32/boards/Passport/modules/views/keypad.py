# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#

import lvgl as lv
from styles.colors import FD_BLUE, TEXT_GREY, VERY_LIGHT_GREY, WHITE
from styles.local_style import LocalStyle
from styles.style import Stylize
from .view import View

WIDTH = 210
HEIGHT = 300
HALF_WIDTH = WIDTH // 2

SIDE_MARGIN = 15
TOP_MARGIN = 10
NUMKEY_HGAP = 10
NUMKEY_VGAP = 5
KEY_WIDTH = 50
KEY_HEIGHT = 24

Keys = [
    ['1', '2', '3'],
    ['4', '5', '6'],
    ['7', '8', '9'],
    ['*', '0', '#'],
]


PALETTE_WHITE = 0
PALETTE_BLACK = 1
PALETTE_DARK_GREY = 2
PALETTE_FD_BLUE = 3


class Keypad(View):
    """Displays a keypad model with keys pressed"""

    def __init__(self):
        super().__init__()

        self.set_size(lv.pct(100), lv.pct(100))

        self.key_state = {
            '1': {'pressed': False, 'released': False, 'frame': None},
            '2': {'pressed': False, 'released': False, 'frame': None},
            '3': {'pressed': False, 'released': False, 'frame': None},
            '4': {'pressed': False, 'released': False, 'frame': None},
            '5': {'pressed': False, 'released': False, 'frame': None},
            '6': {'pressed': False, 'released': False, 'frame': None},
            '7': {'pressed': False, 'released': False, 'frame': None},
            '8': {'pressed': False, 'released': False, 'frame': None},
            '9': {'pressed': False, 'released': False, 'frame': None},
            '0': {'pressed': False, 'released': False, 'frame': None},
            '*': {'pressed': False, 'released': False, 'frame': None},
            '#': {'pressed': False, 'released': False, 'frame': None},
            'l': {'pressed': False, 'released': False, 'frame': None},
            'r': {'pressed': False, 'released': False, 'frame': None},
            'u': {'pressed': False, 'released': False, 'frame': None},
            'd': {'pressed': False, 'released': False, 'frame': None},
            'x': {'pressed': False, 'released': False, 'frame': None},
            'y': {'pressed': False, 'released': False, 'frame': None},
        }

        y = TOP_MARGIN
        self.add_key('u', HALF_WIDTH - KEY_WIDTH // 4, y, small=True)
        self.add_key('d', HALF_WIDTH - KEY_WIDTH // 4, y + NUMKEY_VGAP + KEY_HEIGHT, small=True)
        self.add_key('l', HALF_WIDTH - KEY_WIDTH // 4 - NUMKEY_HGAP -
                     KEY_WIDTH // 2, y + (NUMKEY_VGAP + KEY_HEIGHT) // 2, small=True)
        self.add_key('r', HALF_WIDTH - KEY_WIDTH // 4 + NUMKEY_HGAP +
                     KEY_WIDTH // 2, y + (NUMKEY_VGAP + KEY_HEIGHT) // 2, small=True)
        self.add_key('x', SIDE_MARGIN, y + (NUMKEY_VGAP + KEY_HEIGHT) // 2, small=True)
        self.add_key('y', WIDTH - SIDE_MARGIN - KEY_WIDTH // 2, y + (NUMKEY_VGAP + KEY_HEIGHT) // 2, small=True)

        y += NUMKEY_VGAP + (NUMKEY_VGAP + KEY_HEIGHT) * 2

        # Draw the Numeric keypad grid
        for row in range(len(Keys)):
            for col in range(len(Keys[row])):
                key = Keys[row][col]
                key_x = (SIDE_MARGIN + SIDE_MARGIN // 2) + (col * (KEY_WIDTH + NUMKEY_HGAP))
                key_y = y + row * (KEY_HEIGHT + NUMKEY_VGAP)
                self.add_key(key, key_x, key_y)

    def add_key(self, key, key_x, key_y, small=False):
        from views import Label

        key_frame = View()
        key_frame.set_size(KEY_WIDTH if not small else KEY_WIDTH // 2, KEY_HEIGHT)
        key_frame.set_pos(key_x, key_y)
        key_frame.set_no_scroll()

        # Default style
        with Stylize(key_frame) as frame:
            frame.radius(4)
            frame.border_width(1)
            frame.border_color(TEXT_GREY)
            frame.bg_color(VERY_LIGHT_GREY)

        if key == '#':
            label = '##'
        else:
            label = key
        key_label = Label(text=label, color=TEXT_GREY)
        with Stylize(key_label) as label:
            label.align(lv.ALIGN.CENTER)
            label.text_align(lv.TEXT_ALIGN.CENTER)

        key_frame.add_child(key_label)

        # Save the views mapped by key so we can restyle them later
        # print('key={}'.format(key))
        self.key_state.get(key)['frame'] = key_frame
        self.key_state.get(key)['label'] = key_label

        self.add_child(key_frame)

    def update_key(self, key):
        key_state = self.key_state[key]
        if key_state is not None:
            key_frame = key_state.get('frame')
            if key_frame is not None:
                pressed = key_state.get('pressed')
                released = key_state.get('released')
                with LocalStyle(key_frame) as style:
                    if pressed:
                        style.border_width(3)
                    else:
                        style.border_width(1)
                        style.border_color(TEXT_GREY)

                    if released:
                        style.bg_color(FD_BLUE)
                        style.text_color(WHITE)
                    else:
                        style.bg_color(VERY_LIGHT_GREY)

            key_label = key_state.get('label')
            if key_label is not None:
                with LocalStyle(key_label) as style:
                    if released:
                        style.text_color(WHITE)

    def should_finish(self):
        all_were_pressed = True
        for key in self.key_state:
            if not self.key_state[key]['released']:
                all_were_pressed = False

        return all_were_pressed

    def on_key(self, key, pressed):
        if key in self.key_state:
            # Setting these states is a one-way trip
            if self.key_state.get(key)['pressed'] is False and pressed:
                self.key_state.get(key)['pressed'] = True

            if self.key_state.get(key)['released'] is False and not pressed:
                self.key_state.get(key)['released'] = True

            self.update_key(key)
