# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Export one BIP84 key; the native crypto-account encoder requires two Casa keys."""

import chains
import stash

from common import settings
from data_codecs.qr_type import QRType
from foundation import ur
from public_constants import AF_P2WPKH
from utils import xfp2str


def _append_cbor_uint(result, value):
    assert 0 <= value <= 0xffffffff

    if value < 24:
        result.append(value)
    elif value <= 0xff:
        result.extend(bytes([0x18, value]))
    elif value <= 0xffff:
        result.extend(bytes([0x19, value >> 8, value & 0xff]))
    else:
        result.extend(bytes([0x1a,
                             (value >> 24) & 0xff,
                             (value >> 16) & 0xff,
                             (value >> 8) & 0xff,
                             value & 0xff]))


def create_blockstream_account_cbor(public_key,
                                    chain_code,
                                    master_fingerprint,
                                    account_index,
                                    parent_fingerprint,
                                    coin_type):
    """Encode a BIP84 account in the crypto-account form accepted by Jade."""
    assert coin_type in (0, 1)
    is_testnet = coin_type == 1
    assert len(public_key) == 33
    assert len(chain_code) == 32

    result = bytearray(b'\xa2\x01')
    _append_cbor_uint(result, master_fingerprint)

    # crypto-account outputs[0] -> crypto-output -> p2wpkh -> crypto-hdkey.
    result.extend(b'\x02\x81\xd9\x01\x34\xd9\x01\x94\xd9\x01\x2f')
    result.append(0xa5 if is_testnet else 0xa4)
    result.extend(b'\x03\x58\x21')
    result.extend(public_key)
    result.extend(b'\x04\x58\x20')
    result.extend(chain_code)

    if is_testnet:
        # Omit the default Bitcoin type, matching the native registry encoder.
        result.extend(b'\x05\xd9\x01\x31\xa1\x02\x01')

    result.extend(b'\x06\xd9\x01\x30\xa3\x01\x86')
    _append_cbor_uint(result, 84)
    result.append(0xf5)
    _append_cbor_uint(result, coin_type)
    result.append(0xf5)
    _append_cbor_uint(result, account_index)
    result.append(0xf5)
    result.append(0x02)
    _append_cbor_uint(result, master_fingerprint)
    result.extend(b'\x03\x03\x08')
    _append_cbor_uint(result, parent_fingerprint)

    return bytes(result)


def create_blockstream_export(sw_wallet=None,
                              addr_type=AF_P2WPKH,
                              acct_num=0,
                              multisig=False,
                              legacy=False,
                              export_mode='qr',
                              qr_type=QRType.UR2):
    chain = chains.current_chain()
    coin_type = chain.b44_cointype
    account_path = "m/84'/{}'/{}'".format(coin_type, acct_num)
    parent_path = "m/84'/{}'".format(coin_type)
    master_fingerprint = int(xfp2str(settings.get('xfp')), 16)

    with stash.SensitiveValues() as sv:
        parent = sv.derive_path(parent_path)
        account = sv.derive_path(account_path)
        parent_fingerprint = int(xfp2str(parent.my_fingerprint()), 16)

        cbor = create_blockstream_account_cbor(account.public_key(),
                                               account.chain_code(),
                                               master_fingerprint,
                                               acct_num,
                                               parent_fingerprint,
                                               coin_type)

    accts = [{'fmt': AF_P2WPKH, 'deriv': account_path, 'acct': acct_num}]
    return (ur.new_raw('crypto-account', cbor), accts)


BlockstreamWallet = {
    'label': 'Blockstream',
    'sig_types': [
        {'id': 'single-sig',
         'label': 'Single-sig',
         'addr_type': AF_P2WPKH,
         'create_wallet': create_blockstream_export},
    ],
    'export_modes': [
        {'id': 'qr', 'label': 'QR Code', 'qr_type': QRType.UR2},
    ],
}
