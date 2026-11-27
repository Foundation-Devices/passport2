# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#

# rename_multisig_task.py - Rename the given MultisigWallet


async def rename_multisig_task(on_done, ms, new_name):
    from common import settings
    from multisig_wallet import MultisigWallet
    from constants import MAX_MULTISIG_NAME_LEN

    # Safety check
    existing = MultisigWallet.find_match(ms.M, ms.N, ms.get_xfp_paths())
    assert existing
    assert existing.storage_idx == ms.storage_idx

    new_name = new_name[:MAX_MULTISIG_NAME_LEN]
    lst = settings.get('multisig', [])
    ms.name = new_name

    # Can't modify tuple in place to make it a list, modify, then make a new tuple
    w = lst[ms.storage_idx]
    w = list(w)
    w[0] = new_name
    w = tuple(w)
    lst[ms.storage_idx] = w

    # Update settings
    settings.set('multisig', lst)
    settings.save()

    ms.storage_idx = -1

    await on_done(None)
