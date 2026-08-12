# SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# casa.py - Casa support
#

from .multisig_import import read_multisig_config_from_microsd
import chains
import stash
from utils import xfp2str
from data_codecs.qr_type import QRType
from foundation import ur

CASA_PATH = "m/45'"


def create_casa_export(sw_wallet=None,
                       addr_type=None,
                       acct_num=0,
                       multisig=False,
                       legacy=False,
                       export_mode='qr',
                       qr_type=QRType.UR2):
    # Get public details about wallet.
    #
    # simple text format:
    #   key = value
    # or #comments
    # but value is JSON
    from common import settings

    chain = chains.current_chain()

    if export_mode == 'qr' and qr_type == QRType.UR2:
        with stash.SensitiveValues() as sv:
            is_mainnet = chain.ctype == 'BTC'

            network = ur.NETWORK_MAINNET if is_mainnet else ur.NETWORK_TESTNET
            casa_node = sv.derive_path(CASA_PATH)
            account = ur.new_crypto_account(
                sv.node.public_key(),
                sv.node.chain_code(),
                casa_node.public_key(),
                casa_node.chain_code(),
                master_fingerprint=int(xfp2str(settings.get('xfp')), 16),
                network=network)

            return (account, None)
    else:
        with stash.SensitiveValues() as sv:
            s = '''\
    # Passport Summary File
    # For wallet with master key fingerprint: {xfp}

    Wallet operates on blockchain: {nb}

    For BIP44, this is coin_type '{ct}', and internally we use
    symbol {sym} for this blockchain.

    # IMPORTANT WARNING

    Do **not** deposit to any address in this file unless you have a working
    wallet system that is ready to handle the funds at that address!

    # Top-level, 'master' extended public key ('m/'):

    {xpub}

    # Casa extended public key ("m/45'"):

    {casa_xpub}
    '''.format(nb=chain.name, xpub=chain.serialize_public(sv.node),
               casa_xpub=chain.serialize_public(sv.derive_path(CASA_PATH)),
               sym=chain.ctype, ct=chain.b44_cointype, xfp=xfp2str(settings.get('xfp')))

            return (s, None)  # No 'acct_info'


CasaWallet = {
    'label': 'Casa',
    'sig_types': [
        {'id': 'multisig', 'label': 'Multisig', 'addr_type': None, 'create_wallet': create_casa_export,
         'import_microsd': read_multisig_config_from_microsd}
    ],
    'export_modes': [
        {'id': 'qr', 'label': 'QR Code', 'qr_type': QRType.UR2},
        {'id': 'microsd', 'label': 'microSD', 'filename_pattern': '{xfp}-casa.txt', 'ext': '.txt',
         'filename_pattern_multisig': '{xfp}-casa-multisig.txt', 'ext_multisig': '.txt'}
    ],
    'skip_address_validation': True,
    'skip_multisig_import': True,
    'force_multisig_policy': True
}
