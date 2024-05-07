# SPDX-FileCopyrightText: 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# extensions.py - Config data for all supported extensions
#

from .casa_extension import CasaExtension
from .postmix_extension import PostmixExtension
from .key_manager_extension import KeyManagerExtension
from .theya_extension import TheyaExtension

# Array of all supported extensions.
# Used to build extension menus and UI cards.
supported_extensions = [
    CasaExtension,
    PostmixExtension,
    KeyManagerExtension,
    TheyaExtension,
]

supported_extensions_menu = [
    CasaExtension['menu_item'],
    PostmixExtension['menu_item'],
    KeyManagerExtension['menu_item'],
    TheyaExtension['menu_item'],
]
