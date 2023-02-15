# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# nostr_key_task.py - Task to create a new nostr key

async def nostr_key_task(on_done, num_words, index):
    from trezorcrypto import hmac
    import stash

    path = "m/44'/1237'/0'/0/{}".format(index)
    width = (num_words - 1) * 11 // 8 + 1
    with stash.SensitiveValues() as sv:
        node = sv.derive_path(path)
        entropy = hmac(512, '', node.private_key()).digest()
        seed = entropy[0:width]
    await on_done(seed, None)
