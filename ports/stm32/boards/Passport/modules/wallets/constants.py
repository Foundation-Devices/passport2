# SPDX-FileCopyrightText: 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# constants.py - Software wallet constants
#

SIG_TYPE_SINGLE = 'singlesig'
SIG_TYPE_MULTI = 'multisig'

EXPORT_MODE_QR = 'qr'
EXPORT_MODE_MICROSD = 'microsd'

TXN_FMT_PSBT = 'psbt'

# Wallet export formats (xpub, ypub, zpub or some combination):
# - bitcoin_core
# - electrum
# - generic
XPUB_FMT_BITCOIN_CORE = 'bitcoin_core'
XPUB_FMT_ELECTRUM = 'electrum'
XPUB_FMT_GENERIC = 'generic'

# Multisig import formats (single derivation path or one per signer?):
# - kv
# - kv_multi
# (Do we need to have different importers for these?)
MULTISIG_CONFIG_FMT_KV = 'kv'
MULTISIG_CONFIG_FMT_KV_MULTI = 'kv_multi'
MULTISIG_CONFIG_FMT_JSON = 'json'
