# SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# __init__.py - Simulated replacements for some Foundation code
#

import sys
from urandom import randint, seed
from utime import ticks_ms

IS_SIMULATOR = True
IS_COLOR = sys.argv[6] == 'color'
IS_DEV = True
HAS_FUEL_GAUGE = False


class Noise:
    AVALANCHE = 1
    MCU = 2
    SE = 4
    ALS = 8
    ALL = AVALANCHE | MCU | SE | ALS

    def __init__(self):
        v = ticks_ms()
        # print('Initialize RNG with seed = {}'.format(v))
        seed(v)

    def random_bytes(self, buf, _source):
        for i in range(len(buf)):
            buf[i] = randint(0, 255)


class Powermon:
    def __init__(self):
        pass

    def read(self):
        return (0, 3500)


class System:
    def __init__(self):
        self.is_busy = False
        self.user_pubkey = bytearray()
        for i in range(18):
            self.user_pubkey += bytearray(b'\xF0\x0D\xBA\xBE')

        self.device_hash = bytearray()
        for i in range(8):
            self.device_hash += bytearray(b'\xDE\xAD\xBE\xEF')
        # print('device_hash={}'.format(self.device_hash))

        self.brightness = 100

    # Does nothing in simulator
    def turbo(self, enable):
        pass

    def get_serial_number(self):
        return '1111-2222-3333-4444'

    def get_user_firmware_pubkey(self, pubkey):
        pubkey[:] = self.user_pubkey
        return True, pubkey
        # return self.user_pubkey

    def set_user_firmware_pubkey(self, pubkey):
        if len(pubkey) == 64:
            self.user_pubkey = bytearray(pubkey)
            return True
        return False

    def is_user_firmware_installed(self):
        return False

    def get_software_info(self):
        return('v1.0.0', 0, 1, True, 'Jun 27, 2022')

    def get_device_hash(self, hash_buf):
        for i in range(len(self.device_hash)):
            hash_buf[i] = self.device_hash[i]
        return None

    def reset(self):
        sys.exit()

    def shutdown(self):
        sys.exit()

    def get_sd_root(self):
        import ffilib
        import os

        libc = ffilib.libc()
        path = bytearray(500)
        cwd = libc.func("s", "getcwd", "pi")(path, len(path))

        # print('sd_root={}'.format(cwd + '/microsd'))
        return cwd + '/microsd'

    def get_screen_brightness(self, _default):
        return self.brightness

    def set_screen_brightness(self, brightness):
        self.brightness = brightness

    def busy_wait(self, delay_ms):
        from utime import ticks_ms
        start_ticks = ticks_ms()
        end_ticks = start_ticks
        while (end_ticks - start_ticks < delay_ms):
            end_ticks = ticks_ms()

    def validate_firmware_header(self, buf):
        return (True, '2.0.1', None, False)

    def enable_lv_refresh(self, enable):
        pass

# Always "passes"


def verify_supply_chain_server_signature(hash, signature):
    return True


# Always "passes"
def supply_chain_challenge(challenge, response):
    return True


class SettingsFlash:
    def __init__(self):
        pass


class Backlight:
    def __init__(self):
        pass

    def intensity(self, value):
        pass


class FuelGauge:
    def __init__(self):
        pass

    def get_voltage(self):
        return 4200

    def get_battery_percentage(self):
        return 100

    def get_temperature(self):
        return 77

    def get_time_to_empty(self):
        return 0

    def read(self, command):
        pass

    def do_test(self):
        return True
