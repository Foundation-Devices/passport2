# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# nostr_key_task.py - Task to create a new nostr key


async def nostr_key_task(on_done, index):
    import stash
    from foundation import secp256k1
    from utils import nostr_nip19_from_key

    path = "m/44'/1237'/{}'/0/0".format(index)
    with stash.SensitiveValues() as sv:
        node = sv.derive_path(path)
        key = node.private_key()
    pub = secp256k1.public_key_schnorr(key)
    nsec = nostr_nip19_from_key(key, "nsec")
    npub = nostr_nip19_from_key(pub, "npub")
    await on_done({'priv': nsec, 'npub': npub, 'pk': key, 'pub': pub}, None)
