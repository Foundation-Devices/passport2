# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# delay_task.py - Task to wait a specific amount of time


async def delay_task(on_done, delay_ms, busy_wait):
    from uasyncio import sleep_ms
    import common

    # If busy_wait is true, then we drop to C and do a real hard loop, otherwise we do a more friendly
    # async sleep that gives other MicroPython tasks a chance to run.

    if busy_wait:
        common.system.busy_wait(delay_ms)
    else:
        await sleep_ms(delay_ms)

    await on_done(None)
