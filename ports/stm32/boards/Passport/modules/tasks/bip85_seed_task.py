# SPDX-FileCopyrightText: 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# bip85_seed_task.py - Task to create a new seed using BIP 85

async def bip85_seed_task(on_done, index):
    from serializations import sha512
    import stash
    path = "m/83696968'/39'/0'/24'/{}'".format(index)

    with stash.SensitiveValues() as sv:
        node = sv.derive_path(path)
        entropy = sha512(node.private_key())
        seed = entropy[0:32]
    await on_done(seed, None)
