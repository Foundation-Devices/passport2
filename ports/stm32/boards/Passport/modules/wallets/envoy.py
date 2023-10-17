# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# envoy.py - Envoy support
#

import stash
import ujson
import chains
import common
from utils import to_str, get_accounts
from data_codecs.qr_type import QRType
from public_constants import AF_CLASSIC, AF_P2WPKH, AF_P2TR
from foundation import ur
import passport

# from .multisig_json import create_multisig_json_wallet
# from .multisig_import import read_multisig_config_from_qr, read_multisig_config_from_microsd
from .utils import get_bip_num_from_addr_type


def create_envoy_export(sw_wallet=None,
                        addr_type=None,
                        acct_num=0,
                        multisig=False,
                        legacy=False,
                        export_mode='qr',
                        qr_type=QRType.UR2):
    # Generate line-by-line JSON details about wallet.
    #
    # Adapted from Electrum format, but simplified for Envoy use
    from common import settings, system

    serial_num = system.get_serial_number()
    fw_version = 'v{}'.format(system.get_software_info()[0])

    chain = chains.current_chain()

    accounts = get_accounts()
    acct_name = ''
    if accounts is not None and len(accounts) > 0:
        for acct in accounts:
            if acct.get('acct_num') == acct_num:
                acct_name = acct.get('name', None)
                break

    # Try to use the account name from the active account if no real account was found by the lookup.
    # Used for extension accounts like Postmix.
    if acct_name == '':
        acct = common.ui.get_active_account()
        if acct is not None:
            acct_name = acct.get('name', '')

    device_name = common.settings.get('device_name', '')

    rv = dict(acct_name=acct_name,
              acct_num=acct_num,
              hw_version=1.2 if passport.IS_COLOR else 1,
              fw_version=fw_version,
              serial=serial_num,
              device_name=device_name)

    for name, mode in [
        ('bip84', 84),
        ('bip86', 86)
    ]:
        with stash.SensitiveValues() as sv:
            acct_path = "m/{mode}'/{coin}'/{acct}'".format(
                mode=mode,
                coin=chain.b44_cointype,
                acct=acct_num)

            child_node = sv.derive_path(acct_path)
            xfp = settings.get('xfp')
            xpub = sv.chain.serialize_public(child_node, AF_CLASSIC)
            # print('xfp to export: {}'.format(xfp))
            # print('xpub to export: {}'.format(xpub))

            rv[name] = dict(derivation=acct_path,
                            xfp=xfp,
                            xpub=xpub)

    # Return the possible account mappings that the exported wallet can choose from
    # When we get the address back, we can determine the 'fmt' from the address and then look it up to
    # find the derivation path and account number.
    accts = [{'fmt': addr_type, 'deriv': acct_path, 'acct': acct_num}]

    msg = ujson.dumps(rv)

    if export_mode == 'qr':
        return (ur.new_bytes(msg), accts)
    # print('msg={}'.format(to_str(msg)))

    return (msg, accts)


EnvoyWallet = {
    'label': 'Envoy',
    'sig_types': [
        {'id': 'single-sig', 'label': 'Single-sig', 'addr_type': AF_P2WPKH, 'create_wallet': create_envoy_export},
    ],
    'export_modes': [
        {'id': 'qr', 'label': 'QR Code', 'qr_type': QRType.UR2},
        {'id': 'microsd', 'label': 'microSD', 'filename_pattern': '{xfp}-envoy.json'}
    ],
    'skip_address_validation': False,
    'skip_multisig_import': True,
    'select_addr_type': True,
    'addr_options': [AF_P2WPKH, AF_P2TR],
}
