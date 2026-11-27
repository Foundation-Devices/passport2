# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# delete_multisig_task.py - Delete the given MultisigWallet


async def delete_multisig_task(on_done, ms):
    from common import settings
    from multisig_wallet import MultisigWallet
    from errors import Error

    if ms.storage_idx < 0:
        await on_done(Error.MULTISIG_STORAGE_IDX_ERROR)
        return

    # Safety check
    existing = MultisigWallet.find_match(ms.M, ms.N, ms.get_xfp_paths())
    if not existing or existing.storage_idx != ms.storage_idx:
        await on_done(Error.MULTISIG_STORAGE_IDX_ERROR)
        return

    lst = settings.get('multisig', [])
    del lst[ms.storage_idx]

    # Update settings
    settings.set('multisig', lst)
    settings.save()

    ms.storage_idx = -1

    await on_done(None)
