# SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# electrum.py - Electrum export
#

import stash
import ujson
import chains
from data_codecs.qr_type import QRType
from foundation import ur
from utils import xfp2str, to_str
# from .multisig_json import create_multisig_json_wallet
# from .multisig_import import read_multisig_config_from_qr, read_multisig_config_from_microsd
from public_constants import AF_CLASSIC, AF_P2WPKH, AF_P2WPKH_P2SH
from .utils import get_bip_num_from_addr_type


def create_electrum_export(sw_wallet=None,
                           addr_type=None,
                           acct_num=0,
                           multisig=False,
                           legacy=False,
                           export_mode='qr',
                           qr_type=None):
    # Generate line-by-line JSON details about wallet.
    #
    # Much reverse engineering of Electrum here. It's a complex legacy file format.
    from common import settings

    mode = get_bip_num_from_addr_type(addr_type, multisig)

    chain = chains.current_chain()

    with stash.SensitiveValues() as sv:
        acct_path = "m/{mode}'/{coin}'/{acct}'".format(
            mode=mode,
            coin=chain.b44_cointype,
            acct=acct_num)

        child_node = sv.derive_path(acct_path)
        ckcc_xfp = settings.get('xfp')
        ckcc_xpub = sv.chain.serialize_public(child_node, AF_CLASSIC)
        xpub = sv.chain.serialize_public(child_node, addr_type)
        # print('ckcc_xfp to export: {}'.format(ckcc_xfp))
        # print('ckcc_xpub to export: {}'.format(ckcc_xpub))
        # print('xpub to export: {}'.format(xpub))

    rv = dict(seed_version=17, use_encryption=False, wallet_type='standard')

    label = 'Passport{} ({})'.format(
        ' Acct. #%d' % acct_num if acct_num else '',
        xfp2str(ckcc_xfp))

    rv['keystore'] = dict(ckcc_xfp=ckcc_xfp,
                          ckcc_xpub=ckcc_xpub,
                          hw_type='passport',
                          type='hardware',
                          label=label,
                          derivation=acct_path,
                          xpub=xpub)

    # Return the possible account mappings that the exported wallet can choose from
    # When we get the address back, we can determine the 'fmt' from the address and then look it up to
    # Find the derivation path and account number.
    accts = [{'fmt': addr_type, 'deriv': acct_path, 'acct': acct_num}]
    msg = ujson.dumps(rv)

    if qr_type == QRType.UR2:
        return (ur.new_bytes(msg), accts)

    return (msg, accts)


# Zach found that Electrum will successfully import Passport with this format, while not also thinking that it is
# a Coldcard and expecting a USB connection.
#
# {
#    "keystore":
#    {
#      "ckcc_xpub": "xpub6CFZUBDBeW2VBwrVDs1HKZvpueR7ceTuSY6pLkKdo7okmpw9NGrQYKLE3o4wBUS9aPeYfzxTsbuM4HXnyom8nZgmdJNVqh5mEEMrqDkVJ2g", # noqa
#      "xpub": "zpub6qv65WZ1ws7StYEitaaXjk7qFai1VtSuGm9FuY7QZ8ZWt2ZbsbBXnSeW6Cz7BHjzPftAAx9anvcSprkvRCbAP33yMymM1WijmgV9cPRCgu6", # noqa
#      "label": "Passport (317184B6)",
#      "ckcc_xfp": 3062133041,
#      "type": "bip32",
#      "derivation": "m/84'/0'/0'"
#    },
#    "wallet_type": "standard"}
#
def create_electrum_watch_only_export(sw_wallet=None,
                                      addr_type=None,
                                      acct_num=0,
                                      multisig=False,
                                      legacy=False,
                                      export_mode=None,
                                      qr_type=None):
    from common import settings

    mode = get_bip_num_from_addr_type(addr_type, multisig)

    chain = chains.current_chain()

    with stash.SensitiveValues() as sv:
        acct_path = "m/{mode}'/{coin}'/{acct}'".format(
            mode=mode,
            coin=chain.b44_cointype,
            acct=acct_num)

        # print('acct_path={} addr_type={} multisig={}'.format(acct_path, addr_type, multisig))

        child_node = sv.derive_path(acct_path)
        ckcc_xfp = settings.get('xfp')
        ckcc_xpub = sv.chain.serialize_public(child_node, AF_CLASSIC)
        xpub = sv.chain.serialize_public(child_node, addr_type)
        # print('ckcc_xfp to export: {}'.format(ckcc_xfp))
        # print('ckcc_xpub to export: {}'.format(ckcc_xpub))
        # print('xpub to export: {}'.format(xpub))

    rv = dict(wallet_type='standard')

    label = 'Passport{} ({})'.format(
        ' Acct. #%d' % acct_num if acct_num else '',
        xfp2str(ckcc_xfp))

    rv['keystore'] = dict(ckcc_xpub=ckcc_xpub,
                          xpub=xpub,
                          label=label,
                          ckcc_xfp=ckcc_xfp,
                          type='bip32',
                          derivation=acct_path,
                          )

    # Return the possible account mappings that the exported wallet can choose from
    # When we get the address back, we can determine the 'fmt' from the address and then look it up to
    # Find the derivation path and account number.
    accts = [{'fmt': addr_type, 'deriv': acct_path, 'acct': acct_num}]
    msg = ujson.dumps(rv)
    # print('msg={}'.format(to_str(msg)))
    return (msg, accts)


ElectrumWallet = {
    'label': 'Electrum',
    'sig_types': [
        {'id': 'single-sig', 'label': 'Single-sig', 'addr_type': AF_P2WPKH,
         'create_wallet': create_electrum_watch_only_export},
        # {'id':'multisig', 'label':'Multsig', 'addr_type': None, 'create_wallet': create_multisig_json_wallet,
        #  'import_microsd': read_multisig_config_from_microsd}
    ],
    'export_modes': [
        {'id': 'microsd', 'label': 'microSD', 'filename_pattern': '{xfp}-electrum.json',
         'filename_pattern_multisig': '{xfp}-electrum-multisig.json'}
    ]
}
