# SPDX-FileCopyrightText: 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# bip85_seed_task.py - Task to create a new seed using BIP 85

async def bip85_seed_task(on_done, index):
    from trezorcrypto import hmac
    import stash

    path = "m/83696968'/39'/0'/24'/{}'".format(index)
    with stash.SensitiveValues() as sv:
        node = sv.derive_path(path)
        entropy = hmac(512, 'bip-entropy-from-k', node.private_key()).digest()
        seed = entropy[0:32]
    await on_done(seed, None)
