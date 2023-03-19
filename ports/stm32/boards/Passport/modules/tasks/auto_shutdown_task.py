# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# auto_shutdown_task.py

from uasyncio import sleep_ms
import utime
import common
import passport
from utils import get_screen_brightness


async def auto_shutdown_task():
    if passport.IS_SIMULATOR:
        return

    common.last_interaction_time = utime.ticks_ms()

    while True:
        await sleep_ms(1000)

        # Get timeout in seconds, and current time
        timeout = common.settings.get('shutdown_timeout', 5 * 60)
        now = utime.ticks_ms()

        # Dim screen for 30s before shutdown
        if timeout > 0 and now - common.last_interaction_time >= (timeout - 30) * 1000:
            common.display.set_brightness(2)

        # Shut down if last interaction is longer than (timeout) seconds ago
        if timeout > 0 and now - common.last_interaction_time >= timeout * 1000:
            common.system.shutdown()
