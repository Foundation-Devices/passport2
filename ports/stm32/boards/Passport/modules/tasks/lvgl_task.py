# SPDX-FileCopyrightText: 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# lvgl_task.py - Main LVGL loop

from uasyncio import sleep_ms
from utime import ticks_ms
import lvgl as lv
import passport


async def lvgl_task():
    """
    LVGL task

    Returns early on the end product, and runs in a loop in the simulator.
    """

    if not lv.is_initialized():
        lv.init()

    # Try first using a hardware timer to increment the LVGL tick.
    # print('Starting LVGL task')
    await async_loop()


async def async_loop():
    """Asynchronous loop used to increment LVGL tick counter"""

    global thread_lock

    # Give a short time for the card_task to perform the first render to avoid flicker at startup
    await sleep_ms(100)

    if passport.IS_SIMULATOR:
        last_tick = ticks_ms()
    else:
        last_tick = 0

    while True:
        if passport.IS_SIMULATOR:
            new_tick = ticks_ms()
            elapsed = new_tick - last_tick
            lv.tick_inc(elapsed)
            last_tick = new_tick

        lv.timer_handler()

        await sleep_ms(1)
