# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# coconut.py - Coconut Wallet support
#

from .generic_json_wallet import create_generic_json_wallet
from data_codecs.qr_type import QRType

# Coconut Wallet imports the generic single-sig JSON export (same payload as
# Sparrow) over an animated UR2 QR code. The 'model' tag lets Coconut Wallet
# label the imported wallet "Passport Core".
CoconutWallet = {
    'label': 'Coconut Wallet',
    'model': 'passport-core',
    'sig_types': [
        {'id': 'single-sig', 'label': 'Single-sig', 'addr_type': None,
            'create_wallet': create_generic_json_wallet},
    ],
    'export_modes': [
        {'id': 'qr', 'label': 'QR Code', 'qr_type': QRType.UR2},
    ]
}
