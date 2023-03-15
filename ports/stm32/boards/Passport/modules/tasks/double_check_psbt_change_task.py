# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# double_check_psbt_change_task.py - Iterate through the PSBT and double check the change details


async def double_check_psbt_change_task(on_done, psbt):
    import stash
    from utils import swab32, keypath_to_str
    from errors import Error

    with stash.SensitiveValues() as sv:
        # Double check the change outputs are right. This is slow, but critical because
        # it detects bad actors, not bugs or mistakes.
        # - equivalent check already done for p2sh outputs when we re-built the redeem script.
        change_outs = [n for n, o in enumerate(psbt.outputs) if o.is_change]
        if change_outs:

            for count, out_idx in enumerate(change_outs):
                # only expecting single case, but be general

                oup = psbt.outputs[out_idx]

                good = 0
                for pubkey, subpath in oup.subpaths.items():
                    if subpath[0] != psbt.my_xfp and subpath[0] != swab32(psbt.my_xfp):
                        # For multisig, will be N paths, and exactly one will be our key.
                        # For single-signer, should always be my XFP.
                        continue

                    # Derive actual pubkey from private
                    skp = keypath_to_str(subpath)
                    node = sv.derive_path(skp)

                    # check the pubkey of this BIP32 node
                    if pubkey == node.public_key():
                        good += 1

                if not good:
                    # print('double_check_psbt_change_task() Fraudulent Change Error')
                    await on_done("Deception regarding change output. BIP32 path doesn't match actual address.",
                                  Error.PSBT_FRAUDULENT_CHANGE_ERROR)
                    return

    # print('double_check_psbt_change_task() OK')
    await on_done(None, None)
