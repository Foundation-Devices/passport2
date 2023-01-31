# SPDX-FileCopyrightText: 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# postmix_extension.py - Postmix extension UI specification

import lvgl as lv
from flows import MenuFlow
from menus import postmix_menu
from utils import is_extension_enabled, toggle_extension_enabled
from styles.colors import LIGHT_GREY, LIGHT_TEXT, WHITE, RED
import microns


# Postmix account for CoinJoin
name = 'postmix'
postmix_account = {'name': 'Postmix', 'acct_num': 2_147_483_646}
icon = lv.ICON_SPIRAL

PostmixExtension = {
    'label': 'Postmix',
    'name': name,
    'toggle': lambda item: toggle_extension_enabled(name),
    'check': lambda: is_extension_enabled(name),
    'icon': icon,
    'card': {
        'right_icon': icon,
        'header_color': LIGHT_GREY,
        'header_fg_color': LIGHT_TEXT,
        'statusbar': {'title': 'ACCOUNT', 'icon': lv.ICON_FOLDER, 'fg_color': WHITE},
        'title': postmix_account.get('name'),
        'page_micron': microns.PageDot,
        'bg_color': RED,
        'flow': MenuFlow,
        'args': {'menu': postmix_menu, 'is_top_level': True},
        'account': postmix_account
    },
}
