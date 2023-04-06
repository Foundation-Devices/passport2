# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# bip85_seed_task.py - Task to create a new seed using BIP 85


async def bip85_24_word_seed_task(on_done, index):
    await bip85_seed_task(on_done, 24, index)


async def bip85_12_word_seed_task(on_done, index):
    await bip85_seed_task(on_done, 12, index)


async def bip85_seed_task(on_done, num_words, index):
    from trezorcrypto import hmac
    from utils import get_width_from_num_words
    import stash

    path = "m/83696968'/39'/0'/{}'/{}'".format(num_words, index)
    width = get_width_from_num_words(num_words)
    with stash.SensitiveValues() as sv:
        node = sv.derive_path(path)
        entropy = hmac(512, 'bip-entropy-from-k', node.private_key()).digest()
        seed = entropy[0:width]
    await on_done({'priv': seed}, None)
