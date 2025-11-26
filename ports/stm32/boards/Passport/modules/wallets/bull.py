# SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# bull.py - Bull Bitcoin wallet support
#

from .generic_json_wallet import create_generic_json_wallet
from .multisig_json import create_multisig_json_wallet
from .multisig_import import read_multisig_config_from_qr, read_multisig_config_from_microsd
from data_codecs.qr_type import QRType

BullBitcoinWallet = {
    'label': 'Bull',
    'sig_types': [
        {'id': 'single-sig', 'label': 'Single-sig', 'addr_type': None, 'create_wallet': create_generic_json_wallet},
    ],
    'export_modes': [
        {'id': 'qr', 'label': 'QR Code', 'qr_type': QRType.UR2},
    ]
}
