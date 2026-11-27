# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# t9.py - A T9-style text input mechanism, but with no word prediction.

import lvgl as lv
from keys import *
from utils import InputMode
from constants import MAX_TEXT_INPUT_LENGTH


class T9:
    lower_alpha_keymap = {
        KEY_2: 'abc',
        KEY_3: 'def',
        KEY_4: 'ghi',
        KEY_5: 'jkl',
        KEY_6: 'mno',
        KEY_7: 'pqrs',
        KEY_8: 'tuv',
        KEY_9: 'wxyz',
        KEY_0: ' ',
    }

    upper_alpha_keymap = {
        KEY_2: 'ABC',
        KEY_3: 'DEF',
        KEY_4: 'GHI',
        KEY_5: 'JKL',
        KEY_6: 'MNO',
        KEY_7: 'PQRS',
        KEY_8: 'TUV',
        KEY_9: 'WXYZ',
        KEY_0: ' ',
    }

    numeric_keymap = {
        KEY_1: '1',
        KEY_2: '2',
        KEY_3: '3',
        KEY_4: '4',
        KEY_5: '5',
        KEY_6: '6',
        KEY_7: '7',
        KEY_8: '8',
        KEY_9: '9',
        KEY_0: '0',
    }

    def __init__(self, text='', cursor_pos=None, mode=InputMode.NUMERIC, numeric_only=False, input_delay=1000,
                 max_length=MAX_TEXT_INPUT_LENGTH, on_ready=None, allow_cursor_keys=True,
                 allow_backspace=True, max_value=2_147_483_646):
        self.text = [ch for ch in text]
        self.cursor_pos = cursor_pos if cursor_pos is not None else len(self.text)
        self.numeric_only = numeric_only
        self.mode = InputMode.NUMERIC if self.numeric_only else mode
        self.input_delay = input_delay
        self.max_length = max_length
        self.on_ready = on_ready
        self.allow_cursor_keys = allow_cursor_keys
        self.allow_backspace = allow_backspace
        self.max_value = max_value

        self.timer = None
        self.map_pos = 0
        self.last_key = None

    def get_text(self):
        return "".join(self.text)

    def get_number(self):
        return int("".join(self.text))

    def set_max_length(self, max_length):
        self.max_length = max_length
        self.cancel_timer()
        self.last_key = None
        self.map_pos = 0

    def get_mode_keymap(self):
        if self.mode == InputMode.NUMERIC:
            return T9.numeric_keymap
        elif self.mode == InputMode.LOWER_ALPHA:
            return T9.lower_alpha_keymap
        elif self.mode == InputMode.UPPER_ALPHA:
            return T9.upper_alpha_keymap
        else:
            assert('Invalid mode in T9')

    def set_mode(self, mode):
        self.mode = mode

    def is_maxed_out(self):
        return self.max_length and len(self.text) >= self.max_length

    def insert(self, ch):
        if not self.is_maxed_out():
            self.text.insert(self.cursor_pos, ch)
            self.advance_cursor()
            self.ready()

    def on_key(self, key):
        # print('t9.on_key({})'.format(key))

        # Cancel any timer
        self.cancel_timer()

        keymap = self.get_mode_keymap()
        if key == lv.KEY.BACKSPACE:
            self.last_key = None
            if self.allow_backspace:
                if self.cursor_pos > 0:
                    # Delete the character to the left of the cursor
                    self.cursor_pos -= 1

                    if len(self.text) > self.cursor_pos:
                        del self.text[self.cursor_pos]

                    # print(' after backspace: text={}: cursor_pos={}'.format(self.text, self.cursor_pos))
                    self.ready()

        elif key == lv.KEY.LEFT:
            self.last_key = None
            if self.allow_cursor_keys:
                # print('  left: pos={} len={} text={}'.format(self.cursor_pos, len(self.text), self.text))
                if self.cursor_pos > 0:
                    self.cursor_pos -= 1

        elif key == lv.KEY.RIGHT:
            self.last_key = None
            if self.allow_cursor_keys:
                # print('  right: pos={} len={} text={}'.format(self.cursor_pos, len(self.text), self.text))
                if self.cursor_pos < len(self.text):
                    self.cursor_pos += 1

        elif key == KEY_aA1:
            self.last_key = None
            if not self.numeric_only:
                self.mode = InputMode.cycle_to_next(self.mode)
            # print('cycle mode: new={}'.format(InputMode.to_str(self.mode)))

        elif key in keymap:
            chars = keymap[key]

            if self.last_key is None:
                if not self.is_maxed_out():
                    ch = chars[0]
                    if self.numeric_only:
                        text = self.text[:]
                        text.insert(self.cursor_pos, ch)

                        # If conversion fails or it's too big, then don't insert the key
                        try:
                            str = "".join(text)
                            value = int(str)
                            if value > self.max_value:
                                return
                        except ValueError:
                            # Take no action
                            return

                    self.text.insert(self.cursor_pos, ch)
                    self.advance_cursor()

                    # No need to start the timer if there is only one possibility
                    if len(chars) > 1:
                        self.last_key = key
                        self.start_timer()
                    else:
                        self.ready()
                        return
                else:
                    # We just canceled the previous timer, but we better signal a ready() to avoid hanging
                    self.ready()

            elif self.last_key == key:
                # print('>>>>>>> CYCLE!!! cursor_pos={}'.format(self.cursor_pos))
                # Cycle through the characters
                self.map_pos = (self.map_pos + 1) % len(chars)
                ch = chars[self.map_pos]
                # print('ch={}'.format(ch))

                # Replace the previous character
                self.text[self.cursor_pos - 1] = ch
                # print('After replace, text: "{}"'.format(self.text))
                if len(chars) > 1:
                    self.last_key = key
                    self.start_timer()
                else:
                    self.ready()

            else:
                self.map_pos = 0

                if not self.is_maxed_out():
                    ch = chars[self.map_pos]
                    # print('ch={}'.format(ch))

                    # print('>>>>>>> APPEND!!! cursor_pos={}'.format(self.cursor_pos))
                    self.text.insert(self.cursor_pos, ch)
                    self.advance_cursor()
                    # print('After insert, text: "{}"'.format(self.text))
                    if len(chars) > 1:
                        self.last_key = key
                        self.start_timer()
                    else:
                        self.ready()
                else:
                    # We just canceled the previous timer, but we better signal a ready() to avoid hanging
                    self.ready()

    def advance_cursor(self):
        # if not self.is_maxed_out():
        # We don't protect against going 1 past the end here, as this makes backspace work properly when the max
        # length is reached.
        #
        # The checks in on_key() should prevent the length from going beyond the max, and therefore keep the cursor
        # to at most max_length + 1.
        self.cursor_pos += 1
        # print('>>>>>>>>>>>>>>>>> 1: cursor_pos={}'.format(self.cursor_pos))

    def start_timer(self):
        # print('Start timer')
        self.cancel_timer()
        self.timer = lv.timer_create(self.on_timer, self.input_delay, None)

    def cancel_timer(self):
        if self.timer is not None:
            # print('Cancel timer')
            self.timer._del()
            self.timer = None

    def ready(self):
        if self.on_ready is not None:
            self.on_ready(self.get_text())

    def on_timer(self, _t):
        # print('Timer fired! =============================================')
        self.cancel_timer()
        self.last_key = None
        self.map_pos = 0
        self.ready()
