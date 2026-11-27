# SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# caravan.py - Caravan wallet support
#

from .multisig_json import create_multisig_json_wallet
from .multisig_import import read_multisig_config_from_microsd

CaravanWallet = {
    'label': 'Caravan',
    'sig_types': [
        {'id': 'multisig', 'label': 'Multisig', 'addr_type': None, 'create_wallet': create_multisig_json_wallet,
         'import_microsd': read_multisig_config_from_microsd}
    ],
    'export_modes': [
        {'id': 'microsd', 'label': 'microSD', 'filename_pattern': '{xfp}-caravan.json',
         'filename_pattern_multisig': '{xfp}-caravan-multisig.json'}
    ]
}
