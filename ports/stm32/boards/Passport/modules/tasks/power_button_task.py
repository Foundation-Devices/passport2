# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# power_button_task.py - Monitors the power button and asks the user if they want to shutdown when pressed


from uasyncio import ThreadSafeFlag
from pyb import Pin, ExtInt

pwr_btn_int_event = ThreadSafeFlag()
disable_button_isr = False


def pwr_btn_int_cb(_):
    global pwr_btn_int_event, disable_button_isr

    if disable_button_isr:
        return

    disable_button_isr = True

    pwr_btn_int_event.set()


pin = Pin('PWR_SW')
irq = ExtInt(pin, ExtInt.IRQ_FALLING,
             Pin.PULL_UP, pwr_btn_int_cb)


async def power_button_task():
    from pages import ShutdownPage
    import common
    import passport
    from uasyncio import sleep_ms

    if not passport.IS_SIMULATOR:
        from micropython import alloc_emergency_exception_buf

        # Allocate the buffer to be able to debug errors occurred within ISR
        alloc_emergency_exception_buf(100)

    global pwr_btn_int_event, disable_button_isr

    while True:
        if passport.IS_SIMULATOR:
            await sleep_ms(10000)
            continue
        else:
            # Wait for a power button pin interrupt.
            await pwr_btn_int_event.wait()

        if common.ui.get_active_card() is not None:
            # Remember what the current page was
            last_active_page = common.ui.get_active_page()

            # Push the shutdown page and get back to the previous page if the shutdown was cancelled.
            await ShutdownPage().show()
            common.ui.pop_page(last_active_page)

        disable_button_isr = False
