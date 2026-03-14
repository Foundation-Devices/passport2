# SPDX-FileCopyrightText: 2023 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# key_manager_extension.py - Key manager extension UI specification

import lvgl as lv
from flows import MenuFlow
from menus import key_manager_menu
from utils import is_extension_enabled, toggle_extension_enabled
from styles.colors import LIGHT_COPPER, LIGHT_GREY, LIGHT_TEXT, WHITE
import microns


name = 'key_manager'
label = 'Key Manager'
icon = 'ICON_ONE_KEY'

KeyManagerExtension = {
    'name': name,
    'menu_item': {
        'icon': icon,
        'label': label,
        'action': lambda item, context: toggle_extension_enabled(name),
        'is_toggle': True,
        'value': lambda context: is_extension_enabled(name),
    },
    'card': {
        'right_icon': icon,
        'header_color': LIGHT_GREY,
        'header_fg_color': LIGHT_TEXT,
        'statusbar': {'title': 'EXTENSION', 'icon': 'ICON_EXTENSIONS', 'fg_color': WHITE},
        'title': label,
        'page_micron': microns.PageDot,
        'bg_color': LIGHT_COPPER,
        'flow': MenuFlow,
        'args': {'menu': key_manager_menu, 'is_top_level': True},
    },
}
