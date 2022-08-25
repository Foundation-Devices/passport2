# SPDX-FileCopyrightText: 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# casa.py - Casa support
#

from .multisig_import import read_multisig_config_from_microsd
import chains
import stash
from utils import xfp2str
from data_codecs.qr_type import QRType
from ur2.cbor_lite import CBOREncoder
from ur2.ur import UR


def create_casa_export(sw_wallet=None, addr_type=None, acct_num=0, multisig=False, legacy=False, export_mode='qr',):
    # Get public details about wallet.
    #
    # simple text format:
    #   key = value
    # or #comments
    # but value is JSON
    from common import settings

    chain = chains.current_chain()

    if export_mode == 'qr':
        # crypto-hdkey spec: https://github.com/BlockchainCommons/Research/blob/master/papers/bcr-2020-007-hdkey.md
        #
        # Casa `crypto-hdkey` CDDL:
        # {
        #     is-private: false,
        #     key-data: bytes,
        #     chain-code: bytes,
        #     use-info: {
        #         type: cointype-btc,
        #         network: testnet-btc
        #     },
        #     origin: {
        #         source-fingerprint: uint32,
        #         depth: uint8
        #     },
        #     parent-fingerprint: uint32
        # }
        with stash.SensitiveValues() as sv:
            # Encoder
            encoder = CBOREncoder()
            is_mainnet = chain.ctype == 'BTC'
            pk = sv.node.public_key()
            cc = sv.node.chain_code()

            # Map size of 6
            encoder.encodeMapSize(6)
            # Tag 2: is-private
            encoder.encodeUnsigned(2)
            encoder.encodeBool(False)
            # Tag 3: key-data
            encoder.encodeUnsigned(3)
            encoder.encodeBytes(bytearray(pk))
            # Tag 4: chain-code
            encoder.encodeUnsigned(4)
            encoder.encodeBytes(bytearray(cc))
            # Tag 5 (305): use-info
            encoder.encodeUnsigned(5)
            encoder.encodeUndefined(305)
            encoder.encodeMapSize(2)
            # use-info Tag 1: type 0 = BTC
            encoder.encodeUnsigned(1)
            encoder.encodeUnsigned(0)
            # use-info Tag 2: network 0 = Mainnet=0, Testnet=1
            encoder.encodeUnsigned(2)
            encoder.encodeUnsigned(0 if is_mainnet else 1)
            # Tag 6 (304): origin
            encoder.encodeUnsigned(6)
            encoder.encodeUndefined(304)
            encoder.encodeMapSize(2)
            # origin Tag 2: source-fingerprint
            encoder.encodeUnsigned(2)
            encoder.encodeUnsigned(int(xfp2str(settings.get('xfp')), 16))
            # origin Tag 3: depth = 0 (Always depth zero for Casa)
            encoder.encodeUnsigned(3)
            encoder.encodeUnsigned(0)
            # Tag 8: parent-fingerprint
            encoder.encodeUnsigned(8)
            encoder.encodeUnsigned(0)

            import binascii
            print('encoder.get_bytes() = {}'.format(binascii.hexlify(bytearray(encoder.get_bytes()))))
            return (UR('crypto-hdkey', encoder.get_bytes()), None)
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
    '''.format(nb=chain.name, xpub=chain.serialize_public(sv.node),
               sym=chain.ctype, ct=chain.b44_cointype, xfp=xfp2str(settings.get('xfp')))

            print('create_casa_export() returning:\n{}'.format(s))
            return (s, None)  # No 'acct_info'


CasaWallet = {
    'label': 'Casa',
    'sig_types': [
        {'id': 'multisig', 'label': 'Multisig', 'addr_type': None, 'create_wallet': create_casa_export,
         'import_microsd': read_multisig_config_from_microsd}
    ],
    'export_modes': [
        {'id': 'qr', 'label': 'QR Code', 'qr_type': QRType.UR2, 'ur_type': 'crypto-hdkey', 'is_cbor': True},
        {'id': 'microsd', 'label': 'microSD', 'filename_pattern': '{sd}/{xfp}-casa.txt', 'ext': '.txt',
         'filename_pattern_multisig': '{sd}/{xfp}-casa-multisig.txt', 'ext_multisig': '.txt'}
    ],
    'skip_address_validation': True,
    'skip_multisig_import': True,
    'force_multisig_policy': True
}
