# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# colors.py

# Standard color bible

import lvgl as lv
import passport

# Sometimes we need just the hex value, so we define them separately, but
# also define an actual LVGL color object.

if passport.IS_COLOR:
    # Shades of grey
    WHITE_HEX = 0xFFFFFF
    BLACK_HEX = 0x000000

    VERY_LIGHT_GREY_HEX = 0xF0F0F0
    LIGHT_GREY_HEX = 0xDDDDDD
    MEDIUM_GREY_HEX = 0xA0A0A0
    MICRON_GREY_HEX = 0x808080
    TEXT_GREY_HEX = 0x666666
    DARK_GREY_HEX = 0x626262
    CHARCOAL_HEX = 0x262626
    RED_HEX = 0xFF0000
    GREEN_HEX = 0x00BB00
    BLUE_HEX = 0x0000FF
    FD_BLUE_HEX = 0x00BDCD
    FD_LIGHT_BLUE_HEX = 0x55EFFC
    FD_DARK_BLUE_HEX = 0x005d64
    COPPER_HEX = 0xBF755F
    LIGHT_COPPER_HEX = 0xD2A794

    CARD_BG_GREY_HEX = 0xF9F7F6
    CARD_BORDER_HEX = 0xFEFEFE
    LIGHT_TEXT_HEX = TEXT_GREY_HEX
    SPINNER_BG_HEX = 0xE0E0E0
    HIGHLIGHT_TEXT_HEX = FD_BLUE_HEX
    MENU_ITEM_BG_HEX = FD_BLUE_HEX
else:
    # On monochrome, white is white, and everything else is black
    # Shades of grey
    invert = False
    if invert:
        WHITE_HEX = 0x000000
        BLACK_HEX = 0xFFFFFF
    else:
        WHITE_HEX = 0xFFFFFF
        BLACK_HEX = 0x000000

    VERY_LIGHT_GREY_HEX = BLACK_HEX
    LIGHT_GREY_HEX = BLACK_HEX
    MEDIUM_GREY_HEX = BLACK_HEX
    MICRON_GREY_HEX = WHITE_HEX
    TEXT_GREY_HEX = BLACK_HEX
    DARK_GREY_HEX = BLACK_HEX
    CHARCOAL_HEX = BLACK_HEX
    RED_HEX = BLACK_HEX
    GREEN_HEX = BLACK_HEX
    BLUE_HEX = BLACK_HEX
    FD_BLUE_HEX = WHITE_HEX
    FD_LIGHT_BLUE_HEX = BLACK_HEX
    FD_DARK_BLUE_HEX = BLACK_HEX
    COPPER_HEX = BLACK_HEX
    LIGHT_COPPER_HEX = BLACK_HEX

    CARD_BG_GREY_HEX = BLACK_HEX
    CARD_BORDER_HEX = BLACK_HEX
    LIGHT_TEXT_HEX = WHITE_HEX
    SPINNER_BG_HEX = WHITE_HEX
    HIGHLIGHT_TEXT_HEX = WHITE_HEX
    MENU_ITEM_BG_HEX = BLACK_HEX

WHITE = lv.color_hex(WHITE_HEX)
VERY_LIGHT_GREY = lv.color_hex(VERY_LIGHT_GREY_HEX)
LIGHT_GREY = lv.color_hex(LIGHT_GREY_HEX)
MEDIUM_GREY = lv.color_hex(MEDIUM_GREY_HEX)
MICRON_GREY = lv.color_hex(MICRON_GREY_HEX)
TEXT_GREY = lv.color_hex(TEXT_GREY_HEX)
DARK_GREY = lv.color_hex(DARK_GREY_HEX)
CHARCOAL = lv.color_hex(CHARCOAL_HEX)
BLACK = lv.color_hex(BLACK_HEX)

# Primary colors (mostly for debugging)
RED = lv.color_hex(RED_HEX)
GREEN = lv.color_hex(GREEN_HEX)
BLUE = lv.color_hex(BLUE_HEX)

# Brand colors
FD_BLUE = lv.color_hex(FD_BLUE_HEX)
FD_LIGHT_BLUE = lv.color_hex(FD_LIGHT_BLUE_HEX)
FD_DARK_BLUE = lv.color_hex(FD_DARK_BLUE_HEX)
COPPER = lv.color_hex(COPPER_HEX)
LIGHT_COPPER = lv.color_hex(LIGHT_COPPER_HEX)

# Component colors
CARD_BG_GREY = lv.color_hex(CARD_BG_GREY_HEX)
CARD_BORDER = lv.color_hex(CARD_BORDER_HEX)
LIGHT_TEXT = lv.color_hex(LIGHT_TEXT_HEX)
HIGHLIGHT_TEXT = lv.color_hex(HIGHLIGHT_TEXT_HEX)
SPINNER_BG = lv.color_hex(SPINNER_BG_HEX)
MENU_ITEM_BG = lv.color_hex(MENU_ITEM_BG_HEX)

# Account Colors
if passport.IS_SIMULATOR:
    # if common.is_color:
    ACCOUNT_COLORS = [
        {'bg': lv.color_hex(0xBF755F), 'fg': WHITE},
        {'bg': lv.color_hex(0x009DB9), 'fg': WHITE},
        {'bg': lv.color_hex(0x007A7A), 'fg': WHITE},
        {'bg': lv.color_hex(0xD68B6E), 'fg': WHITE},
        {'bg': lv.color_hex(0x00BDCD), 'fg': WHITE},
        {'bg': lv.color_hex(0x2B8A7A), 'fg': WHITE},

    ]

    # Special colors
    CASA_PURPLE_HEX = 0x865EFC
    CASA_PURPLE = lv.color_hex(CASA_PURPLE_HEX)
else:
    ACCOUNT_COLORS = [
        {'bg': lv.color_hex(0xB04C40), 'fg': WHITE},
        {'bg': lv.color_hex(0x007088), 'fg': WHITE},
        {'bg': lv.color_hex(0x086C60), 'fg': WHITE},
        {'bg': lv.color_hex(0xF06448), 'fg': WHITE},
        {'bg': lv.color_hex(0x00A0A8), 'fg': WHITE},
        {'bg': lv.color_hex(0x087C68), 'fg': WHITE},
    ]

    # Special colors
    CASA_PURPLE_HEX = 0x966EFC
    CASA_PURPLE = lv.color_hex(CASA_PURPLE_HEX)
