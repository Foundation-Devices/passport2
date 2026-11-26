# SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundation.xyz>
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

    # Give a short time for the card_task to perform the first render to avoid flicker at startup
    await sleep_ms(100)

    while True:
        draw()
        await sleep_ms(1)


_last_tick = None


def draw():
    """Run LVGL's timers and redraw what changed. Also called by code that keeps the
    loop busy for a long time (see progress.py)."""

    global _last_tick

    # On the device a hardware timer advances LVGL's clock.
    if passport.IS_SIMULATOR:
        new_tick = ticks_ms()
        if _last_tick is not None:
            lv.tick_inc(new_tick - _last_tick)
        _last_tick = new_tick

    lv.timer_handler()
