# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# nostr_key_task.py - Task to create a new nostr key


async def nostr_key_task(on_done, index):
    import stash
    import tcc
    from trezorcrypto import secp256k1

    path = "m/44'/1237'/{}'/0/0".format(index)
    with stash.SensitiveValues() as sv:
        node = sv.derive_path(path)
        key = node.private_key()
        pub = secp256k1.publickey(key, True)[1:]
    nsec = tcc.codecs.bech32_plain_encode("nsec", key)
    npub = tcc.codecs.bech32_plain_encode("npub", pub)
    await on_done({'priv': nsec, 'pub': npub}, None)
