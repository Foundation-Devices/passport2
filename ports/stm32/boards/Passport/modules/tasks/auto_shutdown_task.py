# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# auto_shutdown_task.py

from uasyncio import sleep_ms
import utime
import common
import passport
from utils import get_screen_brightness, has_seed


async def auto_shutdown_task():
    if passport.IS_SIMULATOR:
        return

    common.last_interaction_time = utime.ticks_ms()

    while True:
        await sleep_ms(1000)

        # Get timeout in seconds, and current time
        minutes = 5 if has_seed() else 10
        timeout = common.settings.get('shutdown_timeout', minutes * 60)
        now = utime.ticks_ms()

        # Dim screen for 30s before shutdown
        if timeout > 0 and now - common.last_interaction_time >= (timeout - 30) * 1000:
            common.display.set_brightness(2)

        # Shut down if last interaction is longer than (timeout) seconds ago
        if timeout > 0 and now - common.last_interaction_time >= timeout * 1000:
            common.system.shutdown()
