# SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# lvgl_task.py - Main LVGL loop

from uasyncio import sleep_ms
from utime import ticks_ms
import lvgl as lv
import passport

# Made up front, so that restarting after running out of memory needs no allocation.
_system = passport.System()


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

    run_timers()


def run_timers():
    """Run LVGL's timers: input, animations and redrawing the screen."""

    try:
        lv.timer_handler()
    except BaseException as e:
        # An exception that leaves lv_timer_handler() partway, such as a MemoryError
        # while drawing, leaves it marked as running, so it never runs again: the
        # screen and the keys freeze. Nothing can undo that, so restart.
        try:
            import sys
            sys.print_exception(e)
        except BaseException:
            pass
        _system.reset()
