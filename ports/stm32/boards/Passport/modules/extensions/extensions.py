# SPDX-FileCopyrightText: 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# sw_wallets.py - Software wallet config data for all supported wallets
#

from .casa_extension import CasaExtension
from .postmix_extension import PostmixExtension

# Array of all supported software wallets and their attributes.
# Used to build wallet menus and drive their behavior.
supported_extensions = [
    CasaExtension,
    PostmixExtension,
]
