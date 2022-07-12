# SPDX-FileCopyrightText: 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# keypad_manager.py

import lvgl as lv

from utils import time_now_ms

# TODO:
# - Need a way


class KeypadManager:
    def __init__(self, down="0123456789udrlxy*#", up="0123456789udrlxy*#", long="0123456789udrlxy*#",
                 repeat_delay=1000, repeat_speed=100):
        self.time_pressed = {}
        self.down = down
        self.up = up
        self.long = long
        self.repeat_delay = repeat_delay  # How long until repeat mode starts
        self.repeat_speed = repeat_speed  # How many ms between each repeat
        self.repeat_active = False
        self.kcode_state = 0
        self.kcode_last_time_pressed = 0

    # Returns a dictionary of all pressed keys mapped to the elapsed time that each has been pressed.
    # This can be used for things like showing the progress bar for the Hold to Sign functionality.
    def get_all_pressed(self):
        now = time_now_ms()
        pressed = {}
        for key, start_time in self.time_pressed.items():
            pressed[key] = now - start_time
        return pressed

    def __update_kcode_state(self, expected_keys, actual_key):
        # print('kcode: state={} expected={} actual={}'.format(self.kcode_state, expected_key, actual_key))
        if actual_key in expected_keys:
            self.kcode_state += 1
            self.kcode_last_time_pressed = time_now_ms()
            # print('  state advanced to {}'.format(self.kcode_state))
        else:
            self.kcode_state = 0
            # print('  state reset to {}'.format(self.kcode_state))
            # If this key could start a new sequence, then call recursively so we don't skip it
            if actual_key == 'u':
                # print('  second chance for  {}'.format(actual_key))
                self.__check_kcode(actual_key)

    def __check_kcode(self, key):
        if self.kcode_state == 0:
            self.__update_kcode_state('u', key)
        elif self.kcode_state == 1:
            self.__update_kcode_state('u', key)
        elif self.kcode_state == 2:
            self.__update_kcode_state('d', key)
        elif self.kcode_state == 3:
            self.__update_kcode_state('d', key)
        elif self.kcode_state == 4:
            self.__update_kcode_state('l', key)
        elif self.kcode_state == 5:
            self.__update_kcode_state('r', key)
        elif self.kcode_state == 6:
            self.__update_kcode_state('l', key)
        elif self.kcode_state == 7:
            self.__update_kcode_state('r', key)
        elif self.kcode_state == 8:
            self.__update_kcode_state('xy', key)
        elif self.kcode_state == 9:
            self.__update_kcode_state('xy', key)

        self.kcode_imminent()
        self.kcode_complete()

    # If the user seems to be entering the kcode, then the caller should
    # probably not perform the normal button processing
    def kcode_imminent(self):
        # print('kcode_immiment() = {}'.format(True if self.kcode_state >= 8 else False))
        return self.kcode_state >= 8

    def kcode_complete(self):
        # print('kcode_complete game = {}'.format(True if self.kcode_state == 10 else False))
        return self.kcode_state == 10

    def kcode_reset(self):
        # print('kcode_reset()')
        self.kcode_state = 0

    def is_pressed(self, key):
        return key in self.time_pressed

    def clear(self):
        from common import keypad
        keypad.clear_keys()

    # Reset internal state so that all pending kcodes and repeats are forgotten.
    def reset(self):
        self.time_pressed = {}
        self.kcode_state = 0
        self.kcode_last_time_pressed = 0
        self.repeat_active = False

    # Process available keys and time-based long presses/repeats.
    # Return a tuple with an LVGL event and keycode data.
    def get_event(self):
        from common import keypad

        # This awaited sleep is necessary to give the simulator key code a chance to insert keys into the queue
        # Without it, the ux_poll_once() below will never find a key.
        # await sleep_ms(5)  This shouldn't be required with the LVGL architecture

        # See if we have a character in the queue and if so process it
        # Poll for an event
        (key, is_down) = keypad.get_event()

        # if key is not None or is_down is not None:
        #     print('key={} is_down={}'.format(key, is_down))

        if key is None:
            # There was nothing in the queue, so handle the time-dependent events
            now = time_now_ms()
            for k in self.time_pressed:
                # print('k={}  self.down={}  self.repeat={}  self.time_pressed={}'.format(k, self.down,
                #       self.repeat, self.time_pressed))
                # Handle repeats
                if self.repeat_delay is not None and k in self.down:
                    elapsed = now - self.time_pressed[k]
                    if self.repeat_active is False:
                        if elapsed >= self.repeat_delay:
                            self.repeat_active = True
                            self.time_pressed[k] = now
                            return (lv.EVENT.LONG_PRESSED, k)
                    else:
                        if elapsed >= self.repeat_speed:
                            self.time_pressed[k] = now
                            return (lv.EVENT.LONG_PRESSED_REPEAT, k)

            # Handle kcode timeout - User seemed to give up, so go back to normal key processing
            if self.kcode_state > 0 and now - self.kcode_last_time_pressed >= 3000:
                # print('Resetting kcode due to timeout')
                self.kcode_state = 0
            return None

        now = time_now_ms()

        # Handle the event
        if is_down:
            self.__check_kcode(key)

            # Check to see if we are interested in this key event
            if key in self.down:
                self.time_pressed[key] = now
                # print('PRESSED: {}'.format(key))
                return (lv.EVENT.PRESSED, key)

            if key in self.long:
                self.time_pressed[key] = now

        else:  # up
            # Removing this will cancel long presses of the key as well
            if key in self.time_pressed:
                self.repeat_active = False
                del self.time_pressed[key]

            # Check to see if we are interested in this key event
            if key in self.up:
                # print('RELEASED: {}'.format(key))
                return (lv.EVENT.RELEASED, key)
