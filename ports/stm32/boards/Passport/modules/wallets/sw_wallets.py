# SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# sw_wallets.py - Software wallet config data for all supported wallets
#

from .bitcoin_core import BitcoinCoreWallet
from .keeper import KeeperWallet
from .bluewallet import BlueWallet
from .btcpay import BtcPayWallet
from .bull import BullBitcoinWallet
from .casa import CasaWallet
from .coconut import CoconutWallet
from .coinbits import CoinbitsWallet
# from .caravan import CaravanWallet
# from .dux_reserve import DuxReserveWallet
from .electrum import ElectrumWallet
from .envoy import EnvoyWallet
from .fullynoded import FullyNodedWallet
# from .gordian import GordianWallet
# from .lily import LilyWallet
from .nunchuk import NunchukWallet
from .simple_bitcoin_wallet import SimpleBitcoinWallet
from .sparrow import SparrowWallet
from .specter import SpecterWallet
from .theya import TheyaWallet
from .zeus import ZeusWallet
from data_codecs.qr_type import QRType


def create_liana_export(*args, **kwargs):
    # Keep the exporter off the startup import path. Connect Wallet's registry
    # is loaded during boot, when the MicroPython heap is at its tightest.
    from .liana import create_liana_export as export
    return export(*args, **kwargs)


LianaWallet = {
    'label': 'Liana',
    # Liana policy keys always use the BIP48 native-SegWit branch. Treat this
    # as multisig inside ConnectWalletFlow so it does not attempt single-sig
    # address verification before Liana has constructed the complete policy.
    'sig_types': [{
        'id': 'multisig',
        'label': 'Wallet policy',
        'addr_type': None,
        'create_wallet': create_liana_export,
    }],
    'export_modes': [
        {
            'id': 'qr',
            'label': 'QR Code',
            'qr_type': QRType.UR2,
        },
        {
            'id': 'microsd',
            'label': 'microSD',
            'filename_pattern_multisig': '{xfp}-liana-account-{acct}.txt',
            'ext_multisig': '.txt',
        },
    ],
    'skip_multisig_import': True,
    'skip_address_validation': True,
    'custom_text': {
        'pairing_qr':
            'Passport will display an animated account QR.\n\n'
            'Scan it when adding this Passport in Liana.',
        'pairing_microsd':
            'Passport will save a key file to microSD.\n\n'
            'Import it when adding this Passport in Liana.',
        'connection_complete':
            'Liana key exported. After creating the wallet in Liana, export '
            'its descriptor and register it under Wallet Policies.',
    },
}

# Array of all supported software wallets and their attributes.
# Used to build wallet menus and drive their behavior.
supported_software_wallets = [
    EnvoyWallet,
    BitcoinCoreWallet,
    KeeperWallet,
    BlueWallet,
    BtcPayWallet,
    BullBitcoinWallet,
    # CaravanWallet,
    CasaWallet,
    CoconutWallet,
    CoinbitsWallet,
    # DuxReserveWallet,
    ElectrumWallet,
    FullyNodedWallet,
    LianaWallet,
    # GordianWallet,
    # LilyWallet,
    NunchukWallet,
    SimpleBitcoinWallet,
    SparrowWallet,
    SpecterWallet,
    TheyaWallet,
    ZeusWallet,
]
