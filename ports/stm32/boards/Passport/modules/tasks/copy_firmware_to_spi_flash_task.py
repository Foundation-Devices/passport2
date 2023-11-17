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
from common import debug_str


async def copy_firmware_to_spi_flash_task(file_path, size, on_progress, set_text, on_done):
    from common import system, sf

    try:
        with CardSlot() as card:
            with open(file_path, 'rb') as fp:
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

                # Combine them
                s = trezorcrypto.sha256()
                s.update(header_hash)
                s.update(device_hash)

                # Result
                update_hash = s.digest()

                # Erase first page
                sf.sector_erase(0)
                while sf.is_busy():
                    await sleep_ms(10)

                buf = bytearray(256)        # must be flash page size

                # Start one page in so that we can use the first page for storing a hash.
                # The hash combines the firmware hash with the device hash.
                pos = 256
                update_display = 0
                percent = 0
                set_text('Start copy')
                while pos <= size + 256:
                    set_text('pos={}%'.format(pos))
                    # Update progress bar every 50 flash pages
                    if update_display % 50 == 0:
                        percent = int(((pos - 256) / size) * 100)
                        set_text('percent={}%'.format(percent))
                        # print('pos = {} percent={}%'.format(pos, percent))
                        on_progress(percent)
                    update_display += 1

                    set_text('Reading')
                    here = fp.readinto(buf)
                    if not here:
                        set_text('EOF')
                        break

                    set_text('Check erase')
                    if pos % 4096 == 0:
                        set_text('Do erase')
                        # erase here
                        sf.sector_erase(pos)
                        set_text('Erase wait')
                        while sf.is_busy():
                            set_text('Erase wait...')
                            await sleep_ms(10)
                        set_text('Erase done')

                    set_text('Writing...')
                    sf.write(pos, buf)
                    set_text('Writing wait')

                    # full page write: 0.6 to 3ms
                    while sf.is_busy():
                        set_text('Write wait...')
                        await sleep_ms(1)

                    pos += here
                    if passport.IS_SIMULATOR:
                        set_text('WTF?')
                        await sleep_ms(1)

                set_text('Final write 1')
                # Do this at the end so that we know the rest worked - prevent bootloader from installing bad firmware
                buf[0:32] = update_hash  # Copy into the buf we'll use to write to SPI flash

                sf.write(0, buf)  # Need to write the entire page of 256 bytes
                set_text('Final write 2')

                # Success
                await on_done(None)
    except CardMissingError:
        await on_done(Error.MICROSD_CARD_MISSING)

    # print('>>>>>>>>>>>>>>>>>>>>>>>>>>>>> copy_firmware_to_spi_flash_task() is DONE!')
