
# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# make_microsd_file_system_task.py - Create the new FAT file system

import pyb
from errors import Error


async def make_microsd_file_system_task(on_done):
    from os import VfsFat

    sd = pyb.SDCard()
    assert sd

    if not sd.present():
        await on_done(Error.MICROSD_CARD_MISSING)
        return

    # TDOO: Need this function to call lv_refr_now()
    try:
        VfsFat.mkfs(sd)
    except Exception as e:
        await on_done(Error.MICROSD_FORMAT_ERROR)
        return

    # Important: turn off power
    sd = pyb.SDCard()
    sd.power(0)

    await on_done(None)
