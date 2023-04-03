# SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# generic_json_wallet.py - Generic JSON Wallet export
#

import chains
import ujson
import stash
from utils import xfp2str, to_str
from common import settings
from public_constants import AF_CLASSIC, AF_P2WPKH, AF_P2WPKH_P2SH, AF_P2WSH_P2SH, AF_P2WSH, AF_P2TR
from data_codecs.qr_type import QRType
from foundation import ur


def create_generic_json_wallet(sw_wallet=None,
                               addr_type=None,
                               acct_num=0,
                               multisig=False,
                               legacy=False,
                               export_mode='qr',
                               qr_type=QRType.UR2):
    # Generate data that other programers will use to import from (single-signer)

    chain = chains.current_chain()
    rv = dict(chain=chain.ctype,
              # Don't include these for privacy reasons
              xpub=settings.get('xpub'),
              xfp=xfp2str(settings.get('xfp')),
              account=acct_num)

    accts = []

    with stash.SensitiveValues() as sv:
        # Each of these paths will have /{change}/{idx} in usage (not hardened)
        for name, deriv, fmt, atype, is_multisig in [
            ('bip44', "m/44'/{coin_type}'/{acct}'", AF_CLASSIC, 'p2pkh', False),
            ('bip49', "m/49'/{coin_type}'/{acct}'", AF_P2WPKH_P2SH, 'p2sh-p2wpkh', False),   # was "p2wpkh-p2sh"
            ('bip84', "m/84'/{coin_type}'/{acct}'", AF_P2WPKH, 'p2wpkh', False),
            ('bip48_1', "m/48'/{coin_type}'/{acct}'/1'", AF_P2WSH_P2SH, 'p2sh-p2wsh', True),
            ('bip48_2', "m/48'/{coin_type}'/{acct}'/2'", AF_P2WSH, 'p2wsh', True),
            # TODO: test if this should be multisig or not, or if another entry is needed
            ('bip86', "m/86'/{coin_type}'/{acct}'", AF_P2TR, 'p2tr', True),
        ]:
            dd = deriv.format(coin_type=chain.b44_cointype, acct=acct_num)
            node = sv.derive_path(dd)
            xfp = xfp2str(node.my_fingerprint())
            xp = chain.serialize_public(node, AF_CLASSIC)
            zp = chain.serialize_public(node, fmt) if fmt != AF_CLASSIC else None

            if is_multisig:
                first_address = None
            else:
                #  Include first non-change address for single-sig wallets: 0/0
                node.derive(0)
                node.derive(0)
                first_address = chain.address(node, fmt)

            accts.append({'fmt': fmt, 'deriv': dd, 'acct': acct_num, 'xfp': xfp})

            rv[name] = dict(deriv=dd, xpub=xp, xfp=xfp, first=first_address, name=atype)
            if zp:
                rv[name]['_pub'] = zp

    msg = ujson.dumps(rv)

    if export_mode == 'qr' and qr_type == QRType.UR2:
        return (ur.new_bytes(msg), accts)

    return (msg, accts)
