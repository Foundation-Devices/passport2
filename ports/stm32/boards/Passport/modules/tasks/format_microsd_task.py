# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# format_microsd_task.py - Format the currently inserted microSD card

import callgate
import pyb
import os
from uasyncio import sleep_ms
from errors import Error


async def format_microsd_task(on_progress, on_done):
    # Erase and re-format SD card. Not a fully secure erase, because that is too slow.
    from common import system
    sd_root = system.get_sd_root()

    try:
        os.umount(sd_root)
    except BaseException:
        pass

    sd = pyb.SDCard()
    assert sd

    if not sd.present():
        await on_done(Error.MICROSD_CARD_MISSING)
        return

    # power cycle so card details (like size) are re-read from current card
    sd.power(0)
    sd.power(1)

    cutoff = 1024       # arbitrary
    blk = bytearray(512)

    # Just get one block of random data and write the same block
    callgate.fill_random(blk)

    last_percent = 0
    on_progress(0)
    await sleep_ms(1)
    for bnum in range(cutoff):
        sd.writeblocks(bnum, blk)

        # Updating about every 10%, otherwise it just slows everything down
        percent = int((bnum / cutoff) * 100)
        if percent - last_percent >= 10:
            last_percent = percent
            on_progress(percent)
            await sleep_ms(1)

    await on_done(None)
