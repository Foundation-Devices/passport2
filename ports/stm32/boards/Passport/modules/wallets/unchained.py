# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# unchained.py - Unchained wallet support

import chains
import stash

from common import settings
from data_codecs.qr_type import QRType
from foundation import ur
from public_constants import AF_P2SH
from utils import swab32

from .multisig_import import read_multisig_config_from_microsd, read_multisig_config_from_qr
from .multisig_json import create_multisig_json_wallet


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


def create_unchained_hdkey_cbor(public_key,
                                chain_code,
                                source_fingerprint,
                                parent_fingerprint,
                                is_testnet):
    """Encode the BIP45 xpub in the crypto-hdkey form accepted by Unchained."""
    assert len(public_key) == 33
    assert len(chain_code) == 32

    result = bytearray()
    # Keys 3, 4, 5, and 6 are required; key 8 is optional.
    result.append(0xa4 + int(parent_fingerprint != 0))
    result.extend(b'\x03\x58\x21')
    result.extend(public_key)
    result.extend(b'\x04\x58\x20')
    result.extend(chain_code)

    # Unchained's decoder currently requires the original BCR-2020 tags.
    result.extend(b'\x05\xd9\x01\x31')  # crypto-coin-info, tag 305
    result.extend(b'\xa1\x02\x01' if is_testnet else b'\xa0')

    result.extend(b'\x06\xd9\x01\x30')  # crypto-keypath, tag 304
    # Keys 1 and 3 are required; key 2 is optional.
    result.append(0xa2 + int(source_fingerprint != 0))
    result.extend(b'\x01\x82\x18\x2d\xf5')  # m/45'
    if source_fingerprint:
        result.append(0x02)
        _append_cbor_uint(result, source_fingerprint)
    result.extend(b'\x03\x01')  # depth 1

    if parent_fingerprint:
        result.append(0x08)
        _append_cbor_uint(result, parent_fingerprint)

    return bytes(result)


def create_unchained_export(sw_wallet=None,
                            addr_type=None,
                            acct_num=0,
                            multisig=False,
                            legacy=False,
                            export_mode='qr',
                            qr_type=QRType.UR2):
    assert multisig

    # Unchained's QR registration is BIP45-only. The Sparrow-style microSD
    # export includes BIP45 plus nested and native BIP48 keys.
    if export_mode != 'qr':
        return create_multisig_json_wallet(sw_wallet=sw_wallet,
                                           addr_type=addr_type,
                                           acct_num=acct_num,
                                           multisig=multisig,
                                           legacy=legacy,
                                           export_mode=export_mode,
                                           qr_type=qr_type)

    chain = chains.current_chain()
    with stash.SensitiveValues() as sv:
        node = sv.derive_path("m/45'")
        source_fingerprint = swab32(settings.get('xfp'))
        cbor = create_unchained_hdkey_cbor(node.public_key(),
                                           node.chain_code(),
                                           source_fingerprint,
                                           node.fingerprint(),
                                           chain.ctype != 'BTC')

    return (ur.new_raw('crypto-hdkey', cbor),
            [{'fmt': AF_P2SH, 'deriv': "m/45'", 'acct': acct_num}])


UnchainedWallet = {
    'label': 'Unchained',
    'sig_types': [
        {'id': 'multisig', 'label': 'Multisig', 'addr_type': None,
         'create_wallet': create_unchained_export,
         'import_qr': read_multisig_config_from_qr,
         'import_microsd': read_multisig_config_from_microsd}
    ],
    'export_modes': [
        {'id': 'qr', 'label': 'QR Code', 'qr_type': QRType.UR2},
        {'id': 'microsd', 'label': 'microSD',
         'filename_pattern_multisig': '{xfp}-unchained-multisig.json'}
    ]
}
