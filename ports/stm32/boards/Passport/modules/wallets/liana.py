# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Liana wallet key export."""

import stash

from common import settings
from public_constants import AF_CLASSIC, AF_P2WSH
from utils import xfp2str


def create_liana_export(sw_wallet=None,
                        addr_type=None,
                        acct_num=0,
                        multisig=False,
                        legacy=False,
                        export_mode='microsd',
                        qr_type=None):
    """Export the native-SegWit BIP48 key accepted by Liana.

    Liana uses the same descriptor key for single-key and multisig policy
    branches. The threshold belongs to the completed wallet policy, not to an
    individual signer's extended public key.
    """
    import chains

    chain = chains.current_chain()
    deriv = "m/48'/{coin_type}'/{acct}'/2'".format(
        coin_type=chain.b44_cointype, acct=acct_num)

    with stash.SensitiveValues() as sv:
        node = sv.derive_path(deriv)
        xpub = sv.chain.serialize_public(node, AF_CLASSIC)

    master_xfp = xfp2str(settings.get('xfp')).lower()
    descriptor_key = '[{xfp}/{deriv}]{xpub}\n'.format(
        xfp=master_xfp,
        deriv=deriv[2:],
        xpub=xpub)
    acct_info = [{
        'fmt': AF_P2WSH,
        'deriv': deriv,
        'acct': acct_num,
        'xfp': master_xfp,
    }]

    return (descriptor_key, acct_info)
