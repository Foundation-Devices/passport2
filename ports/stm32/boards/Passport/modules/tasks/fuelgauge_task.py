# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# fuelgauge_task.py - Task for updating the battery level in the UI by reading the fuel gauge

import lvgl as lv
from micropython import const
from passport import fuelgauge
from uasyncio.lock import Lock
import common

# Battery design capacity. In mAh.
_DESIGN_CAPACITY = const(1200)

# A SoC value when battery level is considered low and the user has to be notified.
_LOW_BATTERY_THRESHOLD = const(5)

# A SoC value when battery level is considered extremely low and device is not functional.
_EXTREMELY_LOW_BATTERY_THRESHOLD = const(2)


class InterruptEvent(Lock):
    def __init__(self):
        super().__init__()

        self.pulse_width = 0
        self.locked = True

    def send(self, pulse_width):
        self.pulse_width = pulse_width
        self.release()

    async def wait(self):
        await self.acquire()
        return self.pulse_width


soc_int_event = InterruptEvent()


async def fuelgauge_task():
    '''
    Fuel Gauge task.

    This task monitors the battery using the Fuel Gauge IC.
    Wakes up each second to check the battery parameters.

    Must be created after initializing LVGL as it updates the widgets on the
    first call of the task and subsequently on the interrupt handlers.

    TODO:
        - Update the UI with the SOC.
    '''

    global soc_int_event

    from pages import ShutdownPage
    from utils import is_logged_in
    from styles.colors import COPPER

    # Initialize the fuelgauge module
    fuelgauge.init(_DESIGN_CAPACITY)

    present = fuelgauge.probe()
    if not present:
        # print('Fuel Gauge is not present')
        return

    if not fuelgauge.is_sealed():
        fuelgauge.seal()

    low_warning_shown = False

    # Register BAT_LOW and SOC_INT interrupt callback, the order is important
    # as we take priority on the BAT_LOW interrupt in order to shutdown the system.
    fuelgauge.bat_low_callback(bat_low_cb)
    fuelgauge.soc_int_callback(soc_int_cb)

    while True:
        # Assume 100% battery if it's not present
        soc = 100
        if fuelgauge.is_battery_detected():
            soc = fuelgauge.read_soc()
        # remaining_capacity = fuelgauge.read_remaining_capacity()
        # full_charge_capacity = fuelgauge.read_full_charge_capacity()
        # percent_remaining = int((remaining_capacity / full_charge_capacity) * 100)
        volt = fuelgauge.read_volt()
        temp = fuelgauge.read_temp()

        # print('SoC: {}%'.format(soc))
        # print('percent_remaining: {}%'.format(percent_remaining))
        # print('remaining_capacity: {}'.format(remaining_capacity))
        # print('full_charge_capacity: {}'.format(full_charge_capacity))
        # print('Voltage: {} mV'.format(volt))
        # print('Temperature: {} (10⁻¹ K)'.format(temp))

        common.ui.set_battery_level(soc)

        # If battery is too low, we avoid the doom loop of reboots by shutting down automatically
        if soc <= _EXTREMELY_LOW_BATTERY_THRESHOLD:
            common.system.shutdown()
        elif soc <= _LOW_BATTERY_THRESHOLD and not low_warning_shown and is_logged_in():
            low_warning_shown = True

            # Remember what the current page was
            last_active_page = common.ui.get_active_page()

            # Push the shutdown page and get back to the previous page if the shutdown was cancelled.
            await ShutdownPage(
                icon=lv.LARGE_ICON_ERROR,
                icon_color=COPPER,
                text='Battery low!\n\nShut down Passport now?').show()
            common.ui.pop_page(last_active_page)

        # Wait for a SOC_INT pulse.
        await soc_int_event.wait()


def bat_low_cb(_):
    '''
    '''

    pass


def soc_int_cb(pulse_width):
    '''
    Callback that is called from the Fuel Gauge interrupt handler.

    Provides pulse width in milliseconds of the interrupt pulse.
    '''

    global soc_int_event

    soc_int_event.send(pulse_width)
