# SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# sparrow.py - Sparrow wallet support
#

from .generic_json_wallet import create_generic_json_wallet
from .multisig_json import create_multisig_json_wallet
from .multisig_import import read_multisig_config_from_qr, read_multisig_config_from_microsd
from data_codecs.qr_type import QRType
from public_constants import AF_P2WPKH, AF_P2TR, AF_P2WPKH_P2SH, AF_CLASSIC

SparrowWallet = {
    'label': 'Sparrow',
    'sig_types': [
        {'id': 'single-sig', 'label': 'Single-sig', 'addr_type': None, 'create_wallet': create_generic_json_wallet},
        {'id': 'multisig', 'label': 'Multisig', 'addr_type': None, 'create_wallet': create_multisig_json_wallet,
         'import_qr': read_multisig_config_from_qr, 'import_microsd': read_multisig_config_from_microsd}
    ],
    'export_modes': [
        {'id': 'qr', 'label': 'QR Code', 'qr_type': QRType.UR2},
        {'id': 'microsd', 'label': 'microSD', 'filename_pattern': '{xfp}-sparrow.json',
         'filename_pattern_multisig': '{xfp}-sparrow-multisig.json'}
    ]
}
