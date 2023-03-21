# SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# main.py - Main initialization code
#

import sys
sys.path.append("..")

import gc
from utils import mem_info
# from translations import T, t, set_active_language

mem_info(label='Start main.py:')


def go():
    import common
    import tasks
    import passport
    from utils import get_screen_brightness

    # Initialize the common objects

    # Avalanche noise source
    from passport import Noise
    common.noise = Noise()

    # Initialize the seed of the PRNG in MicroPython with a real random number
    # We only use the PRNG for non-critical randomness that just needs to be fast
    import urandom
    from utils import randint
    urandom.seed(randint(0, 2147483647))

    # Power monitor
    if not passport.IS_COLOR:
        from passport import Powermon
        common.powermon = Powermon()

        # TODO: This shouldn't be required after migration
        # from passport import SettingsFlash
        # f = SettingsFlash()

    # Get the async event loop to pass in where needed
    import uasyncio
    common.loop = uasyncio.get_event_loop()

    # System
    from passport import System
    common.system = System()
    # common.system.show_busy_bar()

    # Setup alternate constants for Gen 1 devices before anyone imports them
    if not passport.IS_COLOR:
        import constants
        constants.set_gen1_constants()

    # Initialize SD card
    from files import CardSlot
    CardSlot.setup()

    # External SPI Flash
    from sflash import SPIFlash
    common.sf = SPIFlash.default()

    # Give a chance for early foundational changes to be applied
    from schema_evolution import handle_schema_evolutions, handle_foundational_evolutions
    uasyncio.run(handle_foundational_evolutions())

    # Initialize user settings from external or internal flash
    from ext_settings import ExtSettings
    from constants import USER_SETTINGS_START, USER_SETTINGS_END, USER_SETTINGS_SLOT_SIZE
    # Settings are external
    common.settings = ExtSettings(
        slots=range(USER_SETTINGS_START, USER_SETTINGS_END, USER_SETTINGS_SLOT_SIZE),
        slot_size=USER_SETTINGS_SLOT_SIZE,
        loop=common.loop,
        name='user_settings')

    # Serial number is used as the encryption key for settings since these are not sensitive values
    serial = common.system.get_serial_number()
    # print('Settings: serial={}'.format(serial))
    import trezorcrypto
    common.settings.set_key(trezorcrypto.sha256(serial).digest())

    # Load the settings for the first time
    # print('Loading settings...')
    common.settings.load()
    # print('=====\nDONE!\n=====')
    # Initialize the external flash cache
    from ext_settings import ExtSettings
    from constants import FLASH_CACHE_START, FLASH_CACHE_END, FLASH_CACHE_SLOT_SIZE
    common.flash_cache = ExtSettings(
        slots=range(FLASH_CACHE_START, FLASH_CACHE_END, FLASH_CACHE_SLOT_SIZE),
        slot_size=FLASH_CACHE_SLOT_SIZE,
        loop=common.loop,
        name='flash_cache')
    common.flash_cache.load()

    # Initialize the display and show the splash screen
    from display import Display
    common.display = Display()

    brightness = get_screen_brightness(100)

    # print('>>>>>> brightness={}'.format(brightness))
    common.display.set_brightness(brightness)

    # Initialize the keypad
    # TODO: Clean up this relationship - Maybe the manager creates the Keypad internally
    from keypad import Keypad
    from keypad_manager import KeypadManager
    common.keypad = Keypad()
    common.keypad_manager = KeypadManager()

    # Show console welcome message
    print("Passport by Foundation Devices Inc. (C) 2021-2022\n")

    try:
        from pincodes import PinAttempt

        common.pa = PinAttempt()
        common.pa.setup(b'')
    except RuntimeError as e:
        # print("Secure Element Problem: %r" % e)
        pass

    from ui.ui import UI
    from screens import MainScreen

    main_screen = MainScreen()
    common.ui = UI(main_screen)

    common.ui.set_theme('color', common.is_dark_theme)

    # Setup LVGL task
    common.loop.create_task(tasks.lvgl_task())

    # Updates the UI when charger cable is plugged or unplugged
    common.loop.create_task(tasks.charge_monitor_task())

    # Monitors for power button and displays shutdown dialog when pressed
    common.loop.create_task(tasks.power_button_task())

    if passport.HAS_FUEL_GAUGE:
        common.loop.create_task(tasks.fuelgauge_task())

    # Setup the main task
    common.loop.create_task(tasks.main_task())

    # Setup the auto-shutdown task
    common.loop.create_task(tasks.auto_shutdown_task())

    gc.collect()


def run_loop():
    import utils

    # Wrapper for better error handling/recovery at top level.
    try:
        # This keeps all async tasks alive, including the main task created above
        from common import loop
        loop.run_forever()
    except BaseException as exc:
        utils.handle_fatal_error(exc)


go()

gc.collect()
mem_info(label='After go():')


run_loop()
