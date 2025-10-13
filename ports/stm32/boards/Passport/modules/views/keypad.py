# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#

import lvgl as lv
from styles.colors import FD_BLUE, TEXT_GREY, VERY_LIGHT_GREY, WHITE, RED
from styles.local_style import LocalStyle
from styles.style import Stylize
from .view import View

# Define custom colors for the keypad
LIGHT_PINK = lv.color_hex(0xFFB6C1)
LIGHT_BLUE = lv.color_hex(0xADD8E6)

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
            '1': {'pressed': 0, 'released': 0, 'frame': None},
            '2': {'pressed': 0, 'released': 0, 'frame': None},
            '3': {'pressed': 0, 'released': 0, 'frame': None},
            '4': {'pressed': 0, 'released': 0, 'frame': None},
            '5': {'pressed': 0, 'released': 0, 'frame': None},
            '6': {'pressed': 0, 'released': 0, 'frame': None},
            '7': {'pressed': 0, 'released': 0, 'frame': None},
            '8': {'pressed': 0, 'released': 0, 'frame': None},
            '9': {'pressed': 0, 'released': 0, 'frame': None},
            '0': {'pressed': 0, 'released': 0, 'frame': None},
            '*': {'pressed': 0, 'released': 0, 'frame': None},
            '#': {'pressed': 0, 'released': 0, 'frame': None},
            'l': {'pressed': 0, 'released': 0, 'frame': None},
            'r': {'pressed': 0, 'released': 0, 'frame': None},
            'u': {'pressed': 0, 'released': 0, 'frame': None},
            'd': {'pressed': 0, 'released': 0, 'frame': None},
            'x': {'pressed': 0, 'released': 0, 'frame': None},
            'y': {'pressed': 0, 'released': 0, 'frame': None},
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
                pressed_count = key_state.get('pressed')
                released_count = key_state.get('released')
                with LocalStyle(key_frame) as style:
                    # Border styling based on pressed count
                    if pressed_count == 0:
                        style.border_width(1)
                        style.border_color(TEXT_GREY)
                    elif pressed_count % 2 == 1:  # odd
                        style.border_width(3)
                        style.border_color(FD_BLUE)
                    else:  # even and > 0
                        style.border_width(3)
                        style.border_color(RED)

                    # Background styling based on released count
                    if released_count == 0:
                        style.bg_color(VERY_LIGHT_GREY)
                    elif released_count % 2 == 1:  # odd
                        style.bg_color(LIGHT_BLUE)
                    else:  # even and > 0
                        style.bg_color(LIGHT_PINK)

            key_label = key_state.get('label')
            if key_label is not None:
                released_count = key_state.get('released')
                with LocalStyle(key_label) as style:
                    # Adjust text color based on background
                    if released_count == 0:
                        style.text_color(TEXT_GREY)
                    else:
                        style.text_color(WHITE)

    def should_finish(self):
        all_were_pressed = True
        for key in self.key_state:
            if self.key_state[key]['released'] == 0:
                all_were_pressed = False

        # Allow pressing all multiple times, exit by pressing the enter key 5 times
        return all_were_pressed and self.key_state['y']['released'] >= 5

    def on_key(self, key, pressed):
        if key in self.key_state:
            # Increment counts on each event
            if pressed:
                self.key_state.get(key)['pressed'] += 1
            else:
                self.key_state.get(key)['released'] += 1

            self.update_key(key)
