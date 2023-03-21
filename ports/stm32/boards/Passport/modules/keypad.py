# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# keypad.py
#
# Read keys from the hardware keypad queue (or simulator).
#

import lvgl as lv
import utime
import common
import passport
from passport_lv import Keypad as _Keypad


# Passing self.key_cb to set_key_cb() doesn't work, so we do this way instead
def global_key_cb(key, is_pressed):
    if common.keypad.intercept_key_cb is not None:
        common.keypad.intercept_key_cb(key, is_pressed)

    common.keypad.key_cb(key, is_pressed)


def feedback(e, f):
    from utils import get_screen_brightness
    common.last_interaction_time = utime.ticks_ms()

    # Un-dim screen if auto-shutdown is in effect
    true_brightness = get_screen_brightness(100)
    if true_brightness != common.display.curr_brightness:
        common.display.set_brightness(true_brightness)


class Keypad:
    def __init__(self):
        import common
        self.keypad = _Keypad()
        self.keypad.set_key_cb(global_key_cb)
        self.intercept_key_cb = None
        self._enable_global_nav_keys = True
        self._disable_nav_and_select_keys = False
        self.anim_counter = 0

        # There is a worker too if this is the simulator
        if passport.IS_SIMULATOR:
            from keypad_worker import KeypadWorker
            kw = KeypadWorker()

        self.last_event_time = utime.ticks_ms()
        # self.last_event_type = None
        # self.is_duplicate_event = False

        self.pending_keys = []

        # Configure keypad with LVGL
        indev_drv = lv.indev_drv_t()
        indev_drv.init()
        indev_drv.type = lv.INDEV_TYPE.KEYPAD
        indev_drv.read_cb = _Keypad.read_cb
        indev_drv.feedback_cb = feedback
        common.keypad_indev = indev_drv.register()

    # If is_pressed is None, then we inject both a press and a release
    def inject(self, key, is_pressed=None):
        if isinstance(key, str):
            key = ord(key)

        if is_pressed is None:
            self.keypad.inject(key, True)
            self.keypad.inject(key, False)
        else:
            self.keypad.inject(key, is_pressed)

    def set_intercept_key_cb(self, key_cb):
        if hasattr(self.keypad, 'intercept_all'):
            self.keypad.intercept_all(key_cb is not None)

        self.intercept_key_cb = key_cb

    def key_cb(self, key, is_pressed):
        if self.is_animating():
            self.pending_keys.append((key, is_pressed))
            return

        # Don't process select and nav keys if disabled
        if self._disable_nav_and_select_keys:
            return

        if key == lv.KEY.ESC:
            common.ui.on_left_select(is_pressed)
        elif key == lv.KEY.ENTER:
            common.ui.on_right_select(is_pressed)

        # Nav keys are only active sometimes, and we only notify on the pressed state, not release
        if self._enable_global_nav_keys is not None and is_pressed:
            if key == lv.KEY.LEFT:
                common.ui.on_nav_left()
            elif key == lv.KEY.RIGHT:
                common.ui.on_nav_right()

    def disable_nav_and_select_keys(self, disable):
        self._disable_nav_and_select_keys = disable

    def enable_global_nav_keys(self, enable):
        original_value = self._enable_global_nav_keys
        self._enable_global_nav_keys = enable
        self.keypad.enable_global_nav_keys(enable)
        return original_value

    def is_global_nav_key(self, key):
        return (key == lv.KEY.ESC or key == lv.KEY.ENTER) or \
               (self._enable_global_nav_keys and (key == lv.KEY.LEFT or key == lv.KEY.RIGHT))

    def set_active_page(self, page):
        self.active_page = page

    def is_animating(self):
        return self.anim_counter > 0

    def set_is_animating(self, is_animating):
        if is_animating:
            self.anim_counter += 1
        elif self.anim_counter > 0:
            self.anim_counter -= 1
        else:
            assert ('Called set_is_animating(False) too many times!')

        if not self.is_animating():
            import gc
            gc.collect()
            # from utils import mem_info
            # mem_info(label='After animation:')
            self.check_pending_keys()

    def clear_pending_keys(self):
        self.pending_keys = []

    def check_pending_keys(self):
        '''Called at the end of an animation or any other time there has been no group connected to the indev
           for a period of time.
        '''
        # print('check_pending_keys 1: pending_keys={}'.format(self.pending_keys))
        while not self.is_animating() and len(self.pending_keys) > 0:
            # print('check_pending_keys 2')
            (key, is_pressed) = self.pending_keys.pop(0)
            # print('--------------------- Consume key check_pending_keys 3: key={}'.format(key))
            if self.is_global_nav_key(key):
                # print('------------------------------------ check_pending_keys 4: {}'.format(key))
                self.key_cb(key, is_pressed)
            else:
                # print('check_pending_keys 5: {} (other key)'.format(key))
                # Send the key to the group
                common.keypad_indev.group.send_data(key)

            # print('check_pending_keys 3: pending_keys={}'.format(self.pending_keys))

    def set_key_repeat(self, key, repeat):
        self.keypad.set_key_repeat(key, repeat)
