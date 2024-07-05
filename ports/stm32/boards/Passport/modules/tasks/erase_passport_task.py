# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# erase_passport_task.py - Task to erase Passport's wallet and reset wallet-related settings

from pincodes import SE_SECRET_LEN
from uasyncio import sleep_ms


async def erase_passport_task(on_done, full_reset):

    from common import pa, settings
    from flows import saved_flow_keys

    if full_reset:
        settings.clear()
    else:
        # Remove wallet-related settings, but leave other settings alone like terms_ok, validated_ok
        settings.remove('xfp')
        settings.remove('xpub')
        settings.remove('words')
        settings.remove('multisig')
        settings.remove('accounts')
        settings.remove('backup_quiz')
        settings.remove('enable_passphrase')
        settings.remove_regex("^ext\\.*")
        settings.remove('next_addrs')
        settings.remove('derived_keys')
        settings.remove('device_name')
        for key in saved_flow_keys:
            settings.remove(key)

    await sleep_ms(1)

    # Save a blank secret (all zeros is a special case)
    empty_secret = bytes(SE_SECRET_LEN)
    pa.change(new_secret=empty_secret)

    await sleep_ms(1)
    settings.save()
    await sleep_ms(1)

    # print('erase_passport_task calling on_done() 1')
    await on_done(None)
    # print('erase_passport_task calling on_done() 2')
