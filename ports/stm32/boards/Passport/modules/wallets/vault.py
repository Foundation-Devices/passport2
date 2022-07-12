# SPDX-FileCopyrightText: 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# vault.py - Export format used by some wallets
#

import chains
import stash
import ujson
from utils import xfp2str, to_str
from public_constants import AF_CLASSIC, AF_P2WPKH, AF_P2WPKH_P2SH


def create_vault_export(sw_wallet=None, addr_type=None, acct_num=0, multisig=False, legacy=False, export_mode='qr'):
    from common import settings, system

    chain = chains.current_chain()

    (fw_version, _, _, _, _) = system.get_software_info()
    acct_path = "84'/{coin_type}'/{acct}'".format(coin_type=chain.b44_cointype, acct=acct_num)
    master_xfp = xfp2str(settings.get('xfp'))

    with stash.SensitiveValues() as sv:
        child_node = sv.derive_path(acct_path)
        xpub = sv.chain.serialize_public(child_node, addr_type)

    msg = ujson.dumps(dict(ExtPubKey=xpub,
                           MasterFingerprint=master_xfp,
                           AccountKeyPath=acct_path,
                           FirmwareVersion=fw_version))

    accts = [{'fmt': AF_P2WPKH, 'deriv': acct_path, 'acct': acct_num}]

    # print('msg={}'.format(to_str(msg)))
    return (msg, accts)
