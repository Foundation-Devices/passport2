# SPDX-FileCopyrightText: © 2024 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# zeus.py - Zeus Wallet support
#

from .electrum import create_electrum_export
from .multisig_json import create_multisig_json_wallet
from .multisig_import import read_multisig_config_from_qr, read_multisig_config_from_microsd
from data_codecs.qr_type import QRType
from public_constants import AF_P2WPKH

ZeusWallet = {
    'label': 'Zeus',
    'sig_types': [
        {'id': 'single-sig', 'label': 'Single-sig', 'addr_type': AF_P2WPKH, 'create_wallet': create_electrum_export}
    ],
    'export_modes': [
        {'id': 'qr', 'label': 'QR Code', 'qr_type': QRType.UR2},
    ]
}
