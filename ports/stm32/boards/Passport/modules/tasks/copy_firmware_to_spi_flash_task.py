# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# copy_firmware_to_spi_flash_task.py - Task to perform the copy to SPI flash and update the UI progress

from constants import FW_HEADER_SIZE, FW_ACTUAL_HEADER_SIZE
import trezorcrypto
import foundation
import passport
from uasyncio import sleep_ms
from files import CardSlot, CardMissingError
from errors import Error


TIMEOUT_MS = 1000


async def sleep_and_timeout(sleep_time_ms, timeout_ms, sf):
    while sf.is_busy():
        await sleep_ms(sleep_time_ms)
        timeout_ms -= sleep_time_ms
        assert timeout_ms > 0, 'Firmware update timed out'


async def copy_firmware_to_spi_flash_task(file_path, size, on_progress, on_done):
    from common import system, sf

    # try:
    with CardSlot() as card:
        with open(file_path, 'rb') as fp:
            try:
                offset = 0

                header = fp.read(FW_HEADER_SIZE)

                # copy binary into serial flash
                fp.seek(offset)

                # Calculate the update request hash so that the booloader knows this was requested by the user, not
                # injected into SPI flash by some external attacker.
                # Hash the firmware header
                header_hash = bytearray(32)

                # Only hash the bytes that contain the passport_firmware_header_t to match what's hashed in
                # the bootloader
                firmware_header = header[0:FW_ACTUAL_HEADER_SIZE]
                foundation.sha256(firmware_header, header_hash)
                foundation.sha256(header_hash, header_hash)  # Double sha

                # Get the device hash
                device_hash = bytearray(32)
                system.get_device_hash(device_hash)
            except CardMissingError:
                await on_done(Error.MICROSD_CARD_MISSING, None)
            except Exception as e:
                error_message = "Error block 1: {}, Info: {}".format(e.__class__.__name__,
                                                                     e.args[0] if len(e.args) == 1 else e.args)
                await on_done(Error.FIRMWARE_UPDATE_FAILED, error_message)
                return

            try:
                # Combine them
                s = trezorcrypto.sha256()
                s.update(header_hash)
                s.update(device_hash)

                # Result
                update_hash = s.digest()

                # Erase first page
                sf.sector_erase(0)
                await sleep_and_timeout(10, TIMEOUT_MS, sf)

                buf = bytearray(256)        # must be flash page size

                # Start one page in so that we can use the first page for storing a hash.
                # The hash combines the firmware hash with the device hash.
                pos = 256
                update_display = 0

            except CardMissingError:
                await on_done(Error.MICROSD_CARD_MISSING, None)
            except Exception as e:
                error_message = "Error block 2: {}, Info: {}".format(e.__class__.__name__,
                                                                     e.args[0] if len(e.args) == 1 else e.args)
                await on_done(Error.FIRMWARE_UPDATE_FAILED, error_message)
                return

            while pos <= size + 256:
                # Update progress bar every 50 flash pages
                if update_display % 50 == 0:
                    percent = int(((pos - 256) / size) * 100)
                    # print('pos = {} percent={}%'.format(pos, percent))
                    on_progress(percent)
                try:
                    here = fp.readinto(buf)
                    if not here:
                        break
                except CardMissingError:
                    await on_done(Error.MICROSD_CARD_MISSING, None)
                except Exception as e:
                    # error_message = "Error block 3: {}, Info: {}".format(e.__class__.__name__,
                    #                                                      e.args[0] if len(e.args) == 1 else e.args)
                    # await on_done(Error.FIRMWARE_UPDATE_FAILED, error_message)
                    # return
                    continue

                update_display += 1

                try:
                    if pos % 4096 == 0:
                        # erase here
                        sf.sector_erase(pos)
                        await sleep_and_timeout(10, TIMEOUT_MS, sf)

                    sf.write(pos, buf)

                    # full page write: 0.6 to 3ms
                    await sleep_and_timeout(1, TIMEOUT_MS, sf)

                    pos += here
                    if passport.IS_SIMULATOR:
                        await sleep_ms(1)
                except CardMissingError:
                    await on_done(Error.MICROSD_CARD_MISSING, None)
                except Exception as e:
                    error_message = "Error block 4: {}, Info: {}".format(e.__class__.__name__,
                                                                         e.args[0] if len(e.args) == 1 else e.args)
                    await on_done(Error.FIRMWARE_UPDATE_FAILED, error_message)
                    return

            try:
                # Do this at the end so that we know the rest worked - prevent bootloader from installing bad firmware
                buf[0:32] = update_hash  # Copy into the buf we'll use to write to SPI flash

                sf.write(0, buf)  # Need to write the entire page of 256 bytes

                # Success
            except CardMissingError:
                await on_done(Error.MICROSD_CARD_MISSING, None)
            except Exception as e:
                error_message = "Error block 5: {}, Info: {}".format(e.__class__.__name__,
                                                                     e.args[0] if len(e.args) == 1 else e.args)
                await on_done(Error.FIRMWARE_UPDATE_FAILED, error_message)
                return
            await on_done(None, None)

    # except CardMissingError:
    #     await on_done(Error.MICROSD_CARD_MISSING, None)
    # except Exception as e:
    #     error_message = "Error: {}, Info: {}".format(e.__class__.__name__,
    #                                                  e.args[0] if len(e.args) == 1 else e.args)
    # await on_done(Error.FIRMWARE_UPDATE_FAILED, error_message)

    # print('>>>>>>>>>>>>>>>>>>>>>>>>>>>>> copy_firmware_to_spi_flash_task() is DONE!')
