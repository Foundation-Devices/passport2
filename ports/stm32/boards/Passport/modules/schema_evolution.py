# SPDX-FileCopyrightText: 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# schema_evolution.py
#
# Update code for converting any stored data formats when moving from an older firmware version to a newer version.
#

import common
import trezorcrypto
from ext_settings import ExtSettings
import passport

# NOTE: The goal should be to mostly add to existing formats in a way that doesn't require schema evolution scripts,
#       but sometimes this is not possible, so this hook exists to handle those, hopefully rare, cases.

from version import Version


# We can't read the existing cache since the user has to be logged in for that, so we will flush the
# the OVC cache and start over for this new firmware.
def init_flash_cache():
    # print('init_flash_cache() BEGIN')
    # Create the cache and erase all the slots -- will be loaded later once the AES key is set
    from constants import FLASH_CACHE_START, FLASH_CACHE_END, FLASH_CACHE_SLOT_SIZE
    new_flash_cache = ExtSettings(
        slots=range(FLASH_CACHE_START, FLASH_CACHE_END, FLASH_CACHE_SLOT_SIZE),
        slot_size=FLASH_CACHE_SLOT_SIZE,
        loop=None,
        name='flash_cache')
    new_flash_cache.erase_all()
    # No need to load it here as the main initialization code in main.py:go() will do that
    # print('init_flash_cache() END')


def migrate_settings():
    # print('migrate_settings() BEGIN')
    # Create the new external flash settings
    from ext_settings import ExtSettings
    from constants import USER_SETTINGS_START, USER_SETTINGS_END, USER_SETTINGS_SLOT_SIZE
    new_settings = ExtSettings(
        slots=range(USER_SETTINGS_START, USER_SETTINGS_END, USER_SETTINGS_SLOT_SIZE),
        slot_size=USER_SETTINGS_SLOT_SIZE,
        loop=None,
        name='user_settings')
    new_settings.erase_all()

    # Serial number is used as the encryption key for settings since these are not sensitive values
    serial = common.system.get_serial_number()
    # print('Settings: serial={}'.format(serial))
    new_settings.set_key(trezorcrypto.sha256(serial).digest())

    # Load here to initialize state so we can set entries into it below, but should be empty at this point
    new_settings.load()

    # Load existing settings from the internal flash
    from settings import Settings
    old_settings = Settings(None)

    # Copy all existing settings from internal flash to external flash
    for key in old_settings.curr_dict:
        value = old_settings.get(key)
        new_settings.set(key, value)
        # print('migrate_settings(): Copying {} = {}'.format(key, value))

    # Force a save
    new_settings.save()

    # Erase all user settings from the old location - we won't use this anymore
    # TODO: Add this back in before release of FE version of this code
    # old_settings.erase_settings_flash()

    # print('migrate_settings() END')


def handle_foundational_evolutions():
    # This function handles updates that need to be applied very early in the startup cycle before most 'common'
    # values have been configured.  These are "foundational" changes like moving user settings from internal
    # to external flash.  This means that it will need to do "pre-initialization" of some systems that it needs.

    # Only for mono device since color devices will have 2.0.0 as their factory firmware already with user settings
    # in external flash from the beginning.
    if not passport.IS_COLOR:
        from settings import Settings
        old_settings = Settings(None)
        # update_from_to = old_settings.get('update', '1.0.9->2.0.0')
        update_from_to = old_settings.get('update', '2.0.0->2.0.0')
        if update_from_to:
            parts = update_from_to.split('->')
            from_version = Version(parts[0])
            to_version = Version(parts[1])

            # print('handle_foundational_evolutions(): from_version={} -> to_version={}'.format(
            #       from_version, to_version))

            # print("({} or {}) and {}".format(to_version == '1.9.0', to_version == '2.0.0', from_version < to_version))

            # Loop can run multiple times to handle the case of a user skipping firmware versions with data format
            # changes
            if (to_version == '1.9.0' or to_version == '2.0.0') and from_version < to_version:
                # First handle the flash cache migration
                init_flash_cache()

                # Now copy user settings from the internal flash to the external flash
                migrate_settings()


async def handle_schema_evolutions(update_from_to):
    from common import settings

    parts = update_from_to.split('->')
    from_version = parts[0]
    to_version = parts[1]

    # print('handle_schema_evolutions(): from_version={} -> to_version={}'.format(from_version, to_version))

    if to_version == '1.0.7' and from_version < to_version:
        # This no longer used, so clean it out
        settings.remove('backup_num')

        # This is now volatile, so clean it out
        settings.remove('chain')

    # We only reach here if no more evolutions are possible.
    # Remove the update indicator from the settings.
    # NOTE: There is a race condition here, but these evolutions should be extremely fast, and ideally
    #       coded in a way that is idempotent.
    # print('handle_schema_evolutions() Done 1')
    settings.remove('update')
    settings.save()
    # print('handle_schema_evolutions() Done 1')
    return
