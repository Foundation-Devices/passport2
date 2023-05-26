# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# xpub_wallet.py - xpub Wallet export
#

import chains
import stash
from .utils import get_deriv_fmt_from_addr_type
from data_codecs.qr_type import QRType
from foundation import ur


def create_xpub_wallet(sw_wallet=None,
                       addr_type=None,
                       acct_num=0,
                       multisig=False,
                       legacy=False,
                       export_mode='qr',
                       qr_type=QRType.UR2):
    # Generate data that other programers will use to import from (single-signer)

    chain = chains.current_chain()

    with stash.SensitiveValues() as sv:
        # TODO: get the addr_type (AF_P2WPKH for sentinel) here
        deriv = get_deriv_fmt_from_addr_type(addr_type, False)
        print(deriv)
        dd = deriv.format(coin_type=chain.b44_cointype, acct=acct_num)
        node = sv.derive_path(dd)
        pub = chain.serialize_public(node, addr_type)

    if export_mode == 'qr' and qr_type == QRType.UR2:
        return (ur.new_bytes(pub), [])

    return (pub, [])
