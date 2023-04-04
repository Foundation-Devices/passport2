# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# nostr_key_task.py - Task to create a new nostr key


async def nostr_key_task(on_done, index):
    import stash
    import tcc

    path = "m/44'/1237'/{}'/0/0".format(index)
    with stash.SensitiveValues() as sv:
        node = sv.derive_path(path)
        key = node.private_key()
    key = tcc.codecs.bech32_plain_encode("nsec", key)
    await on_done(key, None)
