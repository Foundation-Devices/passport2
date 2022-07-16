# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# colors.py

# Standard color bible

import lvgl as lv
import passport

# Sometimes we need just the hex value, so we define them separately, but
# also define an actual LVGL color object.

# Shades of grey
WHITE_HEX = 0xFFFFFF
WHITE = lv.color_hex(WHITE_HEX)

VERY_LIGHT_GREY_HEX = 0xF0F0F0
VERY_LIGHT_GREY = lv.color_hex(VERY_LIGHT_GREY_HEX)

LIGHT_GREY_HEX = 0xDDDDDD
LIGHT_GREY = lv.color_hex(LIGHT_GREY_HEX)

MEDIUM_GREY_HEX = 0xA0A0A0
MEDIUM_GREY = lv.color_hex(MEDIUM_GREY_HEX)

MICRON_GREY_HEX = 0x808080
MICRON_GREY = lv.color_hex(MICRON_GREY_HEX)

TEXT_GREY_HEX = 0x666666
TEXT_GREY = lv.color_hex(TEXT_GREY_HEX)

DARK_GREY_HEX = 0x626262
DARK_GREY = lv.color_hex(DARK_GREY_HEX)

CHARCOAL_HEX = 0x262626
CHARCOAL = lv.color_hex(CHARCOAL_HEX)

BLACK_HEX = 0x000000
BLACK = lv.color_hex(BLACK_HEX)

# Primary colors (mostly for debugging)
RED_HEX = 0xFF0000
RED = lv.color_hex(RED_HEX)

GREEN_HEX = 0x00BB00
GREEN = lv.color_hex(GREEN_HEX)

BLUE_HEX = 0x0000FF
BLUE = lv.color_hex(BLUE_HEX)

# Brand colors
FD_BLUE_HEX = 0x00BDCD
FD_BLUE = lv.color_hex(FD_BLUE_HEX)

FD_LIGHT_BLUE_HEX = 0x55EFFC
FD_LIGHT_BLUE = lv.color_hex(FD_LIGHT_BLUE_HEX)

FD_PALE_GREY_HEX = 0xE0E0E0
FD_PALE_GREY = lv.color_hex(FD_PALE_GREY_HEX)

FD_DARK_BLUE_HEX = 0x005d64
FD_DARK_BLUE = lv.color_hex(FD_DARK_BLUE_HEX)

COPPER_HEX = 0xBF755F
COPPER = lv.color_hex(COPPER_HEX)

LIGHT_COPPER_HEX = 0xD2A794
LIGHT_COPPER = lv.color_hex(LIGHT_COPPER_HEX)

# Card colors
CARD_BG_GREY_HEX = 0xF9F7F6
CARD_BG_GREY = lv.color_hex(CARD_BG_GREY_HEX)

CARD_BORDER_HEX = 0xFEFEFE
CARD_BORDER = lv.color_hex(CARD_BORDER_HEX)

# Account Colors
if passport.IS_SIMULATOR:
    ACCOUNT_COLORS = [
        {'bg': lv.color_hex(0xBF755F), 'fg': WHITE},
        {'bg': lv.color_hex(0x009DB9), 'fg': WHITE},
        {'bg': lv.color_hex(0x007A7A), 'fg': WHITE},
        {'bg': lv.color_hex(0xD68B6E), 'fg': WHITE},
        {'bg': lv.color_hex(0x00BDCD), 'fg': WHITE},
        {'bg': lv.color_hex(0x2B8A7A), 'fg': WHITE},
    ]
else:
    ACCOUNT_COLORS = [
        {'bg': lv.color_hex(0xB04C40), 'fg': WHITE},
        {'bg': lv.color_hex(0x007088), 'fg': WHITE},
        {'bg': lv.color_hex(0x086C60), 'fg': WHITE},
        {'bg': lv.color_hex(0xF06448), 'fg': WHITE},
        {'bg': lv.color_hex(0x00A0A8), 'fg': WHITE},
        {'bg': lv.color_hex(0x087C68), 'fg': WHITE},
    ]
