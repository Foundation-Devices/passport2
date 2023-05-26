# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# sentinel.py - Sentinel wallet support
#

from .xpub_wallet import create_xpub_wallet
# from .multisig_json import create_multisig_json_wallet
# from .multisig_import import read_multisig_config_from_qr, read_multisig_config_from_microsd
from data_codecs.qr_type import QRType
from public_constants import AF_P2WPKH, AF_CLASSIC

SentinelWallet = {
    'label': 'Sentinel',
    'sig_types': [
        {'id': 'single-sig', 'label': 'Single-sig', 'addr_type': AF_P2WPKH, 'create_wallet': create_xpub_wallet},
        # {'id': 'multisig', 'label': 'Multisig', 'addr_type': None, 'create_wallet': create_multisig_json_wallet,
        #  'import_qr': read_multisig_config_from_qr, 'import_microsd': read_multisig_config_from_microsd}
    ],
    'export_modes': [
        {'id': 'qr', 'label': 'QR Code', 'qr_type': QRType.QR},
        {'id': 'microsd', 'label': 'microSD', 'filename_pattern': '{xfp}-sentinel.txt'}
        # 'filename_pattern_multisig': '{xfp}-nunchuk-multisig.json'}
    ]
}
