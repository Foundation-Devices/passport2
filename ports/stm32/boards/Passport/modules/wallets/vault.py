# SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# vault.py - Export format used by some wallets
#

import chains
import stash
import ujson
from utils import xfp2str, to_str
from public_constants import AF_CLASSIC, AF_P2WPKH, AF_P2WPKH_P2SH, AF_P2TR
from .utils import get_bip_num_from_addr_type


def create_vault_export(sw_wallet=None,
                        addr_type=None,
                        acct_num=0,
                        multisig=False,
                        legacy=False,
                        export_mode='qr',
                        qr_type=None):
    from common import settings, system

    chain = chains.current_chain()

    mode = get_bip_num_from_addr_type(addr_type, multisig)

    (fw_version, _, _, _, _) = system.get_software_info()
    acct_path = "{mode}'/{coin_type}'/{acct}'".format(mode=mode,
                                                      coin_type=chain.b44_cointype,
                                                      acct=acct_num)
    master_xfp = xfp2str(settings.get('xfp'))

    xpub = None
    with stash.SensitiveValues() as sv:
        child_node = sv.derive_path(acct_path)
        xpub = sv.chain.serialize_public(child_node, addr_type)

    rv = dict()

    if addr_type == AF_P2TR:
        rv['Descriptor'] = "tr([{}/{}]{}/0/*)".format(master_xfp, acct_path, xpub)
    else:
        rv['ExtPubKey'] = xpub
        rv['MasterFingerprint'] = master_xfp
        rv['AccountKeyPath'] = acct_path

    rv['FirmwareVersion'] = fw_version
    rv['Source'] = 'Passport'

    msg = ujson.dumps(rv)

    accts = [{'fmt': addr_type, 'deriv': acct_path, 'acct': acct_num}]

    return (msg, accts)
