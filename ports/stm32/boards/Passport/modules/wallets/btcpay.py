# SPDX-FileCopyrightText: 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# btcpay.py - BTCPay wallet support
#

from .vault import create_vault_export
from data_codecs.qr_type import QRType
from public_constants import AF_P2WPKH

BtcPayWallet = {
    'label': 'BTCPay',
    'sig_types': [
        {'id': 'single-sig', 'label': 'Single-sig', 'addr_type': AF_P2WPKH, 'create_wallet': create_vault_export},
    ],
    'address_validation_method': 'show_address',
    'export_modes': [
        {'id': 'qr', 'label': 'QR Code', 'qr_type': QRType.QR},
        {'id': 'microsd', 'label': 'microSD', 'filename_pattern': '{sd}/{xfp}-btcpay.json',
         'filename_pattern_multisig': '{sd}/{xfp}-btcpay-multisig.json'}
    ]
}
