# SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# bitcoin_core.py - Bitcoin Core wallet
#

import stash
import ujson
import chains
from common import settings
from utils import xfp2str


def create_bitcoin_core_export(sw_wallet=None,
                               addr_type=None,
                               acct_num=0,
                               multisig=False,
                               legacy=False,
                               export_mode='qr',
                               qr_type=None):
    import ustruct
    xfp = xfp2str(settings.get('xfp'))

    # make the data
    example_addrs = []
    payload = ujson.dumps(list(generate_bitcoin_core_wallet(example_addrs, acct_num)))

    body = '''\
# Bitcoin Core Wallet Import File

## For wallet with master key fingerprint: {xfp}

Wallet operates on blockchain: {nb}

## Bitcoin Core RPC

The following command can be entered after opening Window -> Console
in Bitcoin Core, or using bitcoin-cli:

importmulti '{payload}'

## Resulting Addresses (first 3)

'''.format(payload=payload, xfp=xfp, nb=chains.current_chain().name)

    body += '\n'.join('%s => %s' % addr for addr in example_addrs)
    body += '\n'

    accts = []  # [ {'fmt':addr_type, 'deriv': acct_path, 'acct': acct_num} ]
    return (body, accts)


def generate_bitcoin_core_wallet(example_addrs, acct_num):
    # Generate the data for an RPC command to import keys into Bitcoin Core
    # - yields dicts for json purposes
    from descriptor import append_checksum

    from public_constants import AF_P2WPKH

    chain = chains.current_chain()

    derive = "84'/{coin_type}'/{account}'".format(account=acct_num, coin_type=chain.b44_cointype)

    with stash.SensitiveValues() as sv:
        prefix = sv.derive_path(derive)
        xpub = chain.serialize_public(prefix)

        for i in range(3):
            sp = '0/%d' % i
            node = sv.derive_path(sp, master=prefix)
            a = chain.address(node, AF_P2WPKH)
            example_addrs.append(('m/%s/%s' % (derive, sp), a))

    xfp = settings.get('xfp')
    txt_xfp = xfp2str(xfp).lower()

    chain = chains.current_chain()

    for internal in [False, True]:
        desc = "wpkh([{fingerprint}/{derive}]{xpub}/{change}/*)".format(
            derive=derive.replace("'", "h"),
            fingerprint=txt_xfp,
            coin_type=chain.b44_cointype,
            account=0,
            xpub=xpub,
            change=(1 if internal else 0))

        yield {
            'desc': append_checksum(desc),
            'range': [0, 1000],
            'timestamp': 'now',
            'internal': internal,
            'keypool': True,
            'watchonly': True
        }


BitcoinCoreWallet = {
    'label': 'Bitcoin Core',
    'sig_types': [
        {'id': 'single-sig', 'label': 'Single-sig', 'addr_type': None, 'create_wallet': create_bitcoin_core_export},
    ],
    'export_modes': [
        {'id': 'microsd', 'label': 'microSD', 'filename_pattern': '{xfp}-bitcoin-core.txt', 'ext': '.txt',
         'filename_pattern_multisig': '{xfp}-bitcoin-core-multisig.json'}
    ]
}
