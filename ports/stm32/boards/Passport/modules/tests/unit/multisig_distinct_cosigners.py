# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Every cosigner in an imported multisig wallet is a different key, whatever
# fingerprint label the config gives it. Both config import and PSBT import
# add cosigners through check_xpub().

import chains
import trezorcrypto

from multisig_wallet import MultisigWallet
from public_constants import AF_P2SH, AF_P2WSH

DERIVATION = "m/48'/0'/0'/2'"
PATH = [0x80000000 | 48, 0x80000000, 0x80000000, 0x80000000 | 2]


def account_node(seed_byte):
    seed = trezorcrypto.bip39.seed(trezorcrypto.bip39.from_data(bytes([seed_byte]) * 16), '')
    node = trezorcrypto.bip32.from_seed(seed, 'secp256k1')
    for element in PATH:
        node.derive(element)
    return node


def add(xpubs, xfp, xpub):
    return MultisigWallet.check_xpub(xfp, xpub, DERIVATION, 'BTC', 0, xpubs)


def assert_refused(xpubs, xfp, xpub):
    count = len(xpubs)
    try:
        add(xpubs, xfp, xpub)
    except AssertionError as exc:
        assert 'Duplicate cosigner key' in str(exc), str(exc)
    else:
        raise AssertionError('a repeated cosigner key was accepted')
    assert len(xpubs) == count


btc = chains.get_chain('BTC')
first, second, third = account_node(1), account_node(2), account_node(3)

xpubs = []
add(xpubs, 0x11111111, btc.serialize_public(first, AF_P2SH))
add(xpubs, 0x22222222, btc.serialize_public(second, AF_P2SH))
assert len(xpubs) == 2

# The same key under another fingerprint label is refused, including when it
# is encoded differently (SLIP-132), since the keys themselves are compared.
assert_refused(xpubs, 0x33333333, btc.serialize_public(first, AF_P2SH))
assert_refused(xpubs, 0x33333333, btc.serialize_public(second, AF_P2WSH))

# A third, distinct key is still accepted.
add(xpubs, 0x33333333, btc.serialize_public(third, AF_P2SH))
assert len(xpubs) == 3

return_value.write(b'OK')
