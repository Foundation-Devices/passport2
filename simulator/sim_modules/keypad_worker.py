# SPDX-FileCopyrightText: 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# keypad.py
#
# Get keycodes from the keypad device driver (they are in a queue)
# and translate them into the required format for KeyInputHandler.
#

import sys
import utime
from uasyncio import StreamReader
from uasyncio.core import get_event_loop

import common


class KeypadWorker:
    def __init__(self):
        fileno = int(sys.argv[2])
        if fileno == -1:
            return

        self.pipe = open(fileno, 'rb')

        loop = get_event_loop()
        loop.create_task(self.worker())

    async def worker(self):
        # Read key presses/releases from the simulator keyboard
        s = StreamReader(self.pipe)

        while 1:
            ln = await s.readline()

            msg = ln[:-1].decode()
            parts = msg.split(':')
            key = ord(parts[0])
            # print('Received: {} {}'.format(key, parts[1]))
            common.keypad.keypad.enqueue_keycode(key, 1 if parts[1] == 'd' else 0)
            if common.keypad.intercept_key_cb is not None:
                common.keypad.intercept_key_cb(key, True if parts[1] == 'd' else False)
