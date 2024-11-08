# SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# simple_bitcoin_wallet.py - Simple Bitcoin Wallet support
#

from .generic_json_wallet import create_generic_json_wallet
from data_codecs.qr_type import QRType

SimpleBitcoinWallet = {
    'label': 'Simple Bitcoin Wallet',
    'sig_types': [
        {'id': 'single-sig', 'label': 'Single-sig', 'addr_type': None,
            'create_wallet': create_generic_json_wallet},
    ],
    'export_modes': [
        {'id': 'qr', 'label': 'QR Code', 'qr_type': QRType.UR2},
    ]
}
