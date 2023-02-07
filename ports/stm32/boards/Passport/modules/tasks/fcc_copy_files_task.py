# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# fcc_copy_files_task.py - Task to perform the copy from microSD to flash and back.

import math
from uasyncio import sleep_ms
from files import CardSlot, CardMissingError
from errors import Error


async def fcc_copy_files_task(file_path, file_size=1024, set_progress=None, set_text=None, on_done=None):
    from common import sf

    # ==========================================================================================================
    # First, write some data to the specified file
    # ==========================================================================================================
    try:
        set_text('Writing Data to File')
        with CardSlot() as card:
            with open(file_path, 'wb') as fp:
                update_display = 0
                buf = bytearray(256)
                num_pages = math.ceil(file_size / 256)
                num_remaining = file_size
                pos = 0
                val = 1
                for p in range(num_pages):
                    num_to_write = min(num_remaining, 256)
                    for i in range(num_to_write):
                        buf[i] = val
                        val += 1
                        if val > 253:
                            val = 1

                    # Write the data in the buffer
                    fp.write(buf[0:num_to_write])
                    pos += num_to_write

                    if update_display % 50 == 0:
                        percent = int((pos / file_size) * 100)
                        # print('Write to File: pos = {} percent={}%'.format(pos, percent))
                        set_progress(percent)
                        await sleep_ms(1)
                    update_display += 1
    except CardMissingError:
        await on_done(Error.MICROSD_CARD_MISSING)
        await sleep_ms(5000)
        return

    # ==========================================================================================================
    # Copy data from file to flash
    # ==========================================================================================================
    try:
        set_text('Copying File to Flash')
        with CardSlot() as card:
            with open(file_path, 'rb') as fp:
                pos = 0
                update_display = 0
                while pos <= file_size:
                    # Update progress bar every 50 flash pages
                    if update_display % 50 == 0:
                        percent = int((pos / file_size) * 100)
                        # print('Copying: pos = {} percent={}%'.format(pos, percent))
                        set_progress(percent)
                        await sleep_ms(10)
                    update_display += 1

                    buf = fp.read(256)
                    if not buf:
                        break
                    bytes_read = len(buf)

                    if pos % 4096 == 0:
                        # erase here
                        sf.sector_erase(pos)
                        while sf.is_busy():
                            await sleep_ms(10)

                    sf.write(pos, buf)

                    while sf.is_busy():
                        await sleep_ms(10)

                    pos += bytes_read

    except CardMissingError:
        await on_done(Error.MICROSD_CARD_MISSING)
        await sleep_ms(5000)
        return

    # ==========================================================================================================
    # Verify that data in flash is correct
    # ==========================================================================================================
    set_text('Verify Data in Flash')
    update_display = 0
    buf = bytearray(256)
    num_pages = math.ceil(file_size / 256)
    num_remaining = file_size
    pos = 0
    offset = 0
    val = 1

    expected_buf = bytearray(256)        # must be flash page size
    actual_buf = bytearray(256)

    for p in range(num_pages):
        num_to_read = min(num_remaining, 256)
        for i in range(num_to_read):
            expected_buf[i] = val
            val += 1
            if val > 253:
                val = 1

        sf.read(offset, actual_buf)

        if expected_buf[0:num_to_read] != actual_buf[0:num_to_read]:
            set_text('Data read back from flash did not match!')
            await sleep_ms(5000)
        # else:
        #     set_text('Verifying')
        #     await sleep_ms(10)

        if update_display % 50 == 0:
            percent = int((pos / file_size) * 100)
            # print('pos = {} percent={}%'.format(pos, percent))
            set_progress(percent)
            await sleep_ms(10)
        update_display += 1

        offset += 256
        pos += 256

    await on_done(None)
    # await sleep_ms(5000)
