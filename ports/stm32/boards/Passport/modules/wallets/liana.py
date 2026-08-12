# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Liana wallet key export."""

import stash

from common import settings
from public_constants import AF_CLASSIC, AF_P2WSH
from utils import xfp2str


def _cbor_head(major, value):
    """Encode one definite-length CBOR head without pulling in a large codec."""
    if value < 24:
        return bytes([(major << 5) | value])
    if value <= 0xff:
        return bytes([(major << 5) | 24, value])
    if value <= 0xffff:
        return bytes([(major << 5) | 25, value >> 8, value & 0xff])
    if value <= 0xffffffff:
        return bytes([(major << 5) | 26,
                      (value >> 24) & 0xff, (value >> 16) & 0xff,
                      (value >> 8) & 0xff, value & 0xff])
    raise ValueError('CBOR integer is too large')


def _cbor_uint(value):
    return _cbor_head(0, value)


def _cbor_bytes(value):
    return _cbor_head(2, len(value)) + bytes(value)


def _cbor_tag(value):
    return _cbor_head(6, value)


def create_liana_crypto_account(master_fingerprint, node, coin_type, acct_num):
    """Build the narrow BCR-2020-015 account profile accepted by Liana."""
    if coin_type not in (0, 1):
        raise ValueError('Liana supports only Bitcoin mainnet or test networks')

    # crypto-hdkey map fields: private, key, chain, use-info, origin, parent-fp.
    hdkey = bytearray(_cbor_head(5, 6))
    hdkey.extend(_cbor_uint(2))
    hdkey.append(0xf4)  # false: this is public key material
    hdkey.extend(_cbor_uint(3))
    hdkey.extend(_cbor_bytes(node.public_key()))
    hdkey.extend(_cbor_uint(4))
    hdkey.extend(_cbor_bytes(node.chain_code()))
    hdkey.extend(_cbor_uint(5))
    hdkey.extend(_cbor_tag(40305))  # crypto-coin-info
    hdkey.extend(_cbor_head(5, 2))
    hdkey.extend(_cbor_uint(1))
    hdkey.extend(_cbor_uint(0))  # Bitcoin
    hdkey.extend(_cbor_uint(2))
    hdkey.extend(_cbor_uint(0 if coin_type == 0 else 1))
    hdkey.extend(_cbor_uint(6))
    hdkey.extend(_cbor_tag(40304))  # crypto-keypath
    hdkey.extend(_cbor_head(5, 3))
    hdkey.extend(_cbor_uint(1))
    hdkey.extend(_cbor_head(4, 8))
    for component in (48, coin_type, acct_num, 2):
        hdkey.extend(_cbor_uint(component))
        hdkey.append(0xf5)  # hardened
    hdkey.extend(_cbor_uint(2))
    hdkey.extend(_cbor_uint(master_fingerprint))
    hdkey.extend(_cbor_uint(3))
    hdkey.extend(_cbor_uint(4))
    hdkey.extend(_cbor_uint(8))
    hdkey.extend(_cbor_uint(node.fingerprint()))

    # crypto-account {master-fingerprint, [wsh(cosigner(crypto-hdkey))]}.
    account = bytearray(_cbor_head(5, 2))
    account.extend(_cbor_uint(1))
    account.extend(_cbor_uint(master_fingerprint))
    account.extend(_cbor_uint(2))
    account.extend(_cbor_head(4, 1))
    account.extend(_cbor_tag(308))   # crypto-output
    account.extend(_cbor_tag(401))   # wsh
    account.extend(_cbor_tag(410))   # cosigner
    account.extend(_cbor_tag(303))   # crypto-hdkey
    account.extend(hdkey)
    return bytes(account)


def create_liana_export(sw_wallet=None,
                        addr_type=None,
                        acct_num=0,
                        multisig=False,
                        legacy=False,
                        export_mode='microsd',
                        qr_type=None):
    """Export the native-SegWit BIP48 key accepted by Liana.

    Liana uses the same descriptor key for single-key and multisig policy
    branches. The threshold belongs to the completed wallet policy, not to an
    individual signer's extended public key.
    """
    import chains

    chain = chains.current_chain()
    deriv = "m/48'/{coin_type}'/{acct}'/2'".format(
        coin_type=chain.b44_cointype, acct=acct_num)
    master_xfp = xfp2str(settings.get('xfp')).lower()

    with stash.SensitiveValues() as sv:
        node = sv.derive_path(deriv)
        xpub = sv.chain.serialize_public(node, AF_CLASSIC)
        if export_mode == 'qr':
            from foundation import ur
            account = create_liana_crypto_account(
                int(master_xfp, 16), node, chain.b44_cointype, acct_num)
            qr_account = ur.new_crypto_account(account)

    descriptor_key = '[{xfp}/{deriv}]{xpub}\n'.format(
        xfp=master_xfp,
        deriv=deriv[2:],
        xpub=xpub)
    acct_info = [{
        'fmt': AF_P2WSH,
        'deriv': deriv,
        'acct': acct_num,
        'xfp': master_xfp,
    }]

    if export_mode == 'qr':
        return (qr_account, acct_info)

    return (descriptor_key, acct_info)
