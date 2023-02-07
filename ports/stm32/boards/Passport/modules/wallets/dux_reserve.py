# SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# dux_reserve.py - Dux Reserve wallet support
#

from .generic_json_wallet import create_generic_json_wallet
from .multisig_json import create_multisig_json_wallet
from .multisig_import import read_multisig_config_from_microsd
from public_constants import AF_P2WPKH

DuxReserveWallet = {
    'label': 'Dux Reserve',
    'sig_types': [
        {'id': 'single-sig', 'label': 'Single-sig', 'addr_type': AF_P2WPKH,
         'create_wallet': create_generic_json_wallet},
        {'id': 'multisig', 'label': 'Multisig', 'addr_type': None, 'create_wallet': create_multisig_json_wallet,
         'import_microsd': read_multisig_config_from_microsd}
    ],
    'export_modes': [
        {'id': 'microsd', 'label': 'microSD', 'filename_pattern': '{sd}/{xfp}-dux.json',
         'filename_pattern_multisig': '{sd}/{xfp}-dux-multisig.json'}
    ]
}
