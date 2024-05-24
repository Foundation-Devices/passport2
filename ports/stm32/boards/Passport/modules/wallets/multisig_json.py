# SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# multisig_json.py - Multisig export format
#

import chains
import stash
import uio
from utils import xfp2str
from common import settings
from public_constants import AF_P2SH, AF_P2WSH, AF_P2WSH_P2SH
from data_codecs.qr_type import QRType
from foundation import ur
from common import system


def create_multisig_json_wallet(sw_wallet=None,
                                addr_type=None,
                                acct_num=0,
                                multisig=False,
                                legacy=False,
                                export_mode='qr',
                                qr_type=QRType.UR2):
    fp = uio.StringIO()
    chain = chains.current_chain()

    fp.write('{\n')
    accts = []
    with stash.SensitiveValues() as sv:

        for deriv, name, fmt in [
            ("m/45'", 'p2sh', AF_P2SH),
            ("m/48'/{coin_type}'/{acct}'/1'", 'p2wsh_p2sh', AF_P2WSH_P2SH),
            ("m/48'/{coin_type}'/{acct}'/2'", 'p2wsh', AF_P2WSH)
        ]:
            # Fill in the acct number
            dd = deriv.format(coin_type=chain.b44_cointype, acct=acct_num)
            node = sv.derive_path(dd)
            xfp = xfp2str(node.my_fingerprint())
            xpub = sv.chain.serialize_public(node, fmt)
            fp.write('  "%s_deriv": "%s",\n' % (name, dd))
            fp.write('  "%s": "%s",\n' % (name, xpub))

            # e.g., AF_P2WSH_P2SH: {'deriv':m/48'/0'/4'/1', 'acct': 4}
            accts.append({'fmt': fmt, 'deriv': dd, 'acct': acct_num})

    if sw_wallet.get('show_fw_version', False):
        version = system.get_software_info()[0]
        fp.write('  "fw_version": "%s",\n' % version)

    xfp = xfp2str(settings.get('xfp', 0))
    fp.write('  "xfp": "%s"\n}\n' % xfp)

    result = fp.getvalue()

    if export_mode == 'qr' and qr_type == QRType.UR2:
        return (ur.new_bytes(result), accts)

    return (result, accts)
