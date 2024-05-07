# SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# sw_wallets.py - Software wallet config data for all supported wallets
#

from .bitcoin_core import BitcoinCoreWallet
from .keeper import KeeperWallet
from .bluewallet import BlueWallet
from .btcpay import BtcPayWallet
from .casa import CasaWallet
# from .caravan import CaravanWallet
# from .dux_reserve import DuxReserveWallet
from .electrum import ElectrumWallet
from .envoy import EnvoyWallet
# from .fullynoded import FullyNodedWallet
# from .gordian import GordianWallet
# from .lily import LilyWallet
from .nunchuk import NunchukWallet
from .simple_bitcoin_wallet import SimpleBitcoinWallet
from .sparrow import SparrowWallet
from .specter import SpecterWallet
from .theya import TheyaWallet

# Array of all supported software wallets and their attributes.
# Used to build wallet menus and drive their behavior.
supported_software_wallets = [
    EnvoyWallet,
    BitcoinCoreWallet,
    KeeperWallet,
    BlueWallet,
    BtcPayWallet,
    # CaravanWallet,
    CasaWallet,
    # DuxReserveWallet,
    ElectrumWallet,
    # FullyNodedWallet,
    # GordianWallet,
    # LilyWallet,
    NunchukWallet,
    SimpleBitcoinWallet,
    SparrowWallet,
    SpecterWallet,
    TheyaWallet,
]
