# SPDX-FileCopyrightText: © 2024 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# coinbits.py - Coinbits support
#

from data_codecs.qr_type import QRType
from public_constants import AF_P2WPKH
from .envoy import create_envoy_export

CoinbitsWallet = {
    'label': 'Coinbits',
    'sig_types': [
        {'id': 'single-sig', 'label': 'Single-sig', 'addr_type': AF_P2WPKH, 'create_wallet': create_envoy_export},
    ],
    'export_modes': [
        {'id': 'qr', 'label': 'QR Code', 'qr_type': QRType.UR2},
        {'id': 'microsd', 'label': 'microSD', 'filename_pattern': '{xfp}-coinbits.json'}
    ],
    'skip_address_validation': False,
    'skip_multisig_import': True,
}
