# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# save_multisig_wallet_task.py - Save the given MultisigWallet


async def save_multisig_wallet_task(on_done, ms):
    # Data to save: Important that this fails immediately when Settings memory would overflow
    from common import settings
    from errors import Error
    from ext_settings import SettingsOutOfSpace

    obj = ms.serialize()

    lst = settings.get('multisig', [])
    original = lst.copy()
    if not lst or ms.storage_idx == -1:
        # New wallet, so append to the end
        ms.storage_idx = len(lst)
        lst.append(obj)
    else:
        # Existing wallet, so update in place
        lst[ms.storage_idx] = obj

    settings.set('multisig', lst)

    # Save now, rather than in background, so we can recover from out-of-space situation
    try:
        settings.save()
    except BaseException as exc:
        # Back out the in-memory change when the save fails for any reason.
        try:
            settings.set('multisig', original)
            settings.save()
            # Shouldn't need to do this since we are going back to the previous values
        except BaseException:
            # Give up on recovery
            pass

        if isinstance(exc, SettingsOutOfSpace):
            await on_done(Error.USER_SETTINGS_FULL)
        else:
            await on_done(Error.USER_SETTINGS_SAVE_FAILED)
        return

    await on_done(None)
