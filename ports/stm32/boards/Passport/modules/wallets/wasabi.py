# SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# wasabi.py - Wasabi wallet
#

from public_constants import AF_P2WPKH, AF_CLASSIC
import chains
import stash
import ujson
from utils import xfp2str, to_str
from common import settings, system


def create_wasabi_export(sw_wallet=None,
                         addr_type=None,
                         acct_num=0,
                         multisig=False,
                         legacy=False,
                         export_mode='qr',
                         qr_type=None):
    # Generate the data for a JSON file which Wasabi can open directly as a new wallet.

    chain = chains.current_chain()

    with stash.SensitiveValues() as sv:
        acct_path = "m/84'/{coin_type}'/{acct}'".format(coin_type=chain.b44_cointype, acct=acct_num)
        node = sv.derive_path(acct_path)
        xfp = xfp2str(settings.get('xfp'))
        xpub = chain.serialize_public(node, AF_CLASSIC)

    assert chain.ctype in {'BTC', 'TBTC'}, "Only Bitcoin supported"

    (fw_version, _, _, _, _) = system.get_software_info()

    rv = dict(MasterFingerprint=xfp,
              ExtPubKey=xpub,
              FirmwareVersion=fw_version)

    accts = [{'fmt': AF_P2WPKH, 'deriv': acct_path, 'acct': acct_num}]
    msg = ujson.dumps(rv)
    # print('msg={}'.format(to_str(msg)))
    return (msg, accts)


WasabiWallet = {
    'label': 'Wasabi',
    'sig_types': [
        {'id': 'single-sig', 'label': 'Single-sig', 'addr_type': AF_P2WPKH, 'create_wallet': create_wasabi_export},
    ],
    'export_modes': [
        {'id': 'microsd', 'label': 'microSD', 'filename_pattern': '{sd}/{xfp}-wasabi.json',
         'filename_pattern_multisig': '{sd}/{xfp}-wasabi-multisig.json'}
    ]
}
