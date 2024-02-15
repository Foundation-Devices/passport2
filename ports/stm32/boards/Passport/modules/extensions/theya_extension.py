# SPDX-FileCopyrightText: 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# theya_extension.py - Theya extension UI specification

import lvgl as lv
from flows import MenuFlow
from menus import theya_menu
from utils import is_extension_enabled, toggle_extension_enabled
from styles.colors import THEYA_YELLOW, LIGHT_GREY, LIGHT_TEXT, WHITE
import microns


name = 'theya'
theya_account = {'name': 'Theya', 'acct_num': 0}
icon = 'ICON_THEYA'

TheyaExtension = {
    'name': name,
    'menu_item': {
        'icon': icon,
        'label': 'Theya',
        'action': lambda item, context: toggle_extension_enabled(name),
        'is_toggle': True,
        'value': lambda context: is_extension_enabled(name),
    },
    'card': {
        'right_icon': icon,
        'header_color': LIGHT_GREY,
        'header_fg_color': LIGHT_TEXT,
        'statusbar': {'title': 'EXTENSION', 'icon': 'ICON_EXTENSIONS', 'fg_color': WHITE},
        'title': theya_account.get('name'),
        'page_micron': microns.PageDot,
        'bg_color': THEYA_YELLOW,
        'flow': MenuFlow,
        'args': {'menu': theya_menu, 'is_top_level': True},
        'account': theya_account
    },
}
