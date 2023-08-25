# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# battery_adc_task.py - Task for updating the battery level in the UI by reading the battery ADC
#                       (Founder's Edition only).


from micropython import const
from uasyncio import sleep_ms
import common

NUM_SAMPLES = const(2)

battery_segments = [
    {'v': 3100, 'p': 100},
    {'v': 3100, 'p': 100},
    {'v': 3025, 'p': 75},
    {'v': 2975, 'p': 50},
    {'v': 2800, 'p': 25},
    {'v': 2400, 'p': 0},
]


def calc_battery_percent(current, voltage):
    # print('calc_battery_percent(): voltage={}'.format(voltage))
    if voltage > 3100:
        voltage = 3100
    elif voltage < 2400:
        voltage = 2400

    # First find the segment we fit in
    for i in range(1, len(battery_segments)):
        curr = battery_segments[i]
        prev = battery_segments[i - 1]
        if voltage >= curr['v']:
            # print('curr[{}]={}'.format(i, curr))

            rise = curr['v'] - prev['v']
            # print('rise={}'.format(rise))

            run = curr['p'] - prev['p']
            # print('run={}'.format(run))

            if run == 0:
                # print('zero run, so return value directly: {}'.format(curr['p']))
                return curr['p']

            # Slope
            m = rise / run
            # print('m={}'.format(m))

            # y = mx + b  =>  x = (y - b) / m  =>  b = y - mx

            # Calculate y intercept for this segment
            b = curr['v'] - (m * curr['p'])
            # print('b={}'.format(b))

            percent = int((voltage - b) / m)
            # print('Returning percent={}'.format(percent))
            return percent

    return 0


async def battery_adc_task():
    import passport
    if not passport.HAS_FUEL_GAUGE:
        return

    while True:
        # Read the current values -- repeat this a number of times and average for better results
        total_current = 0
        total_voltage = 0
        for i in range(NUM_SAMPLES):
            (current, voltage) = common.powermon.read()
            voltage = round(voltage * (44.7 + 22.1) / 44.7)
            total_current += current
            total_voltage += voltage
            await sleep_ms(1)  # Wait a bit before next sample
        current = total_current / NUM_SAMPLES
        voltage = total_voltage / NUM_SAMPLES

        # Update the actual battery level in the UI
        level = calc_battery_percent(current, voltage)
        # print('New battery level = {}'.format(level))

        common.ui.set_battery_level(level)

        # If battery is too low, try to avoid the doom loop of reboots by shutting down automatically
        if level <= 2:
            common.system.shutdown()

        await sleep_ms(60000)
