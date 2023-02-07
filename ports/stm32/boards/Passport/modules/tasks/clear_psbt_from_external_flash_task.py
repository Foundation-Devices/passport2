# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# clear_psbt_from_external_flash_task.py - Task to clear a psbt from external flash after signing for security purposes

from public_constants import TXN_INPUT_OFFSET


async def clear_psbt_from_external_flash_task(on_done, psbt_len):
    from sffile import SFFile

    with SFFile(start=TXN_INPUT_OFFSET, max_size=psbt_len) as out:
        # blank flash
        await out.erase()
    await on_done()
