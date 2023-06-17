# SPDX-FileCopyrightText: 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# casa_extension.py - Casa extension UI specification

import lvgl as lv
from flows import MenuFlow
from menus import casa_menu
from utils import is_extension_enabled, toggle_extension_enabled
from styles.colors import CASA_PURPLE, LIGHT_GREY, LIGHT_TEXT, WHITE
import microns


# Casa account - account number is zero, but they use a special derivation path
name = 'casa'
casa_account = {'name': 'Casa', 'acct_num': 0}
icon = 'ICON_CASA'

CasaExtension = {
    'name': name,
    'menu_item': {
        'icon': icon,
        'label': 'Casa',
        'action': lambda item: toggle_extension_enabled(name),
        'is_toggle': True,
        'value': lambda: is_extension_enabled(name),
    },
    'card': {
        'right_icon': icon,
        'header_color': LIGHT_GREY,
        'header_fg_color': LIGHT_TEXT,
        'statusbar': {'title': 'EXTENSION', 'icon': 'ICON_EXTENSIONS', 'fg_color': WHITE},
        'title': casa_account.get('name'),
        'page_micron': microns.PageDot,
        'bg_color': CASA_PURPLE,
        'flow': MenuFlow,
        'args': {'menu': casa_menu, 'is_top_level': True},
        'account': casa_account
    },
}
