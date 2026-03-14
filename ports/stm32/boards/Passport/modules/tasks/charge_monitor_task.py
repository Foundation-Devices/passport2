# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# charge_monitor_task.py - Updates the UI when charging cable is plugged or unplugged.


from uasyncio import ThreadSafeFlag
from pyb import Pin, ExtInt


chg_stat_b_int_event = ThreadSafeFlag()
disable_isr = False


def chg_stat_b_int_cb(_):
    global chg_stat_b_int_event, disable_isr

    if disable_isr:
        return

    disable_isr = True

    chg_stat_b_int_event.set()


pin = Pin('CHG_STAT_B')
irq = ExtInt(pin, ExtInt.IRQ_RISING_FALLING,
             Pin.PULL_UP, chg_stat_b_int_cb)


async def charge_monitor_task():
    import common
    import passport
    from uasyncio import sleep_ms

    if not passport.IS_SIMULATOR:
        from micropython import alloc_emergency_exception_buf

        # Allocate the buffer to be able to debug errors occurred within ISR
        alloc_emergency_exception_buf(100)

    global chg_stat_b_int_event, disable_isr

    while True:
        if passport.IS_SIMULATOR:
            await sleep_ms(10000)
        else:
            # Update the UI for the first time when charger status pin might be already settled.
            is_charging = pin.value() == 0
            common.ui.set_is_charging(is_charging)

            # Wait for a charger state pin interrupt.
            await chg_stat_b_int_event.wait()

            is_charging = pin.value() == 0
            common.ui.set_is_charging(is_charging)

        disable_isr = False
