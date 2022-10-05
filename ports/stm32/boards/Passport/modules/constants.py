# SPDX-FileCopyrightText: 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# constants.py

import lvgl as lv

# External SPI Flash constants

# ==============================================
# External Flash Layout - Gen 1.2
# ==============================================
# 7,936K  Firmware updates / PSBT signing buffer
#   128K  Flash cache
#   128K  User settings
# ==============================================
# 8,192K  Total external flash size
# ==============================================

# Must write with a multiple of this size
SPI_FLASH_PAGE_SIZE = 256

# Must erase with a multiple of these sizes
SPI_FLASH_SECTOR_SIZE = 4096
SPI_FLASH_BLOCK_SIZE = 65536
SPI_FLASH_TOTAL_SIZE = 8192 * 1024

# Firmware updates

# Gen 1:   1792K = 2048K - 256K for bootloader
# Gen 1.2: 1792K = 2048K - 128K bootloader - 128K user settings
# We use 256 bytes to store an update hash in external flash, so just subtract this off for simplicity
FW_MAX_SIZE = (1792 * 1024) - 256
FW_START = 0
FW_HEADER_SIZE = 2048
FW_ACTUAL_HEADER_SIZE = 170  # passport_firmware_header_t uses this many bytes

# PSBT signing (uses same memory as firmware updates)
PSBT_MAX_SIZE = 7936 * 1024  # Total size available for both input and output

# User Settings - end of memory
USER_SETTINGS_SIZE = 128 * 1024
USER_SETTINGS_START = SPI_FLASH_TOTAL_SIZE - USER_SETTINGS_SIZE
USER_SETTINGS_END = USER_SETTINGS_START + USER_SETTINGS_SIZE
USER_SETTINGS_SLOT_SIZE = 8 * 1024

# Flash cache
FLASH_CACHE_SIZE = 128 * 1024
FLASH_CACHE_START = (USER_SETTINGS_START - FLASH_CACHE_SIZE)
FLASH_CACHE_END = FLASH_CACHE_START + FLASH_CACHE_SIZE
FLASH_CACHE_SLOT_SIZE = 16 * 1024


# Some old values only used when migrating flash cache to next-gen firmware
FLASH_CACHE_SIZE_OLD = None
FLASH_CACHE_START_OLD = None
FLASH_CACHE_END_OLD = None

# Other constants
MAX_PASSPHRASE_LENGTH = 64
MAX_ACCOUNT_NAME_LEN = 20
MAX_MULTISIG_NAME_LEN = 20
MAX_ACCOUNTS = 10


DEFAULT_ACCOUNT_ENTRY = {'name': 'Primary', 'acct_num': 0}

# Unit types for labeling conversions
UNIT_TYPE_BTC = 0
UNIT_TYPE_SATS = 1

# Maximum amount of characters in a text entry screen
MAX_MESSAGE_LEN = 64

# Overall layout sizes
STATUSBAR_HEIGHT = 50
CARD_HEADER_HEIGHT = 41
CARD_CHEVRON_HEIGHT = lv.IMAGE_CARD_BOTTOM.header.h
CARD_PAD_LEFT = 6
CARD_PAD_RIGHT = 6
CARD_PAD_BOTTOM = 18
CARD_BORDER_WIDTH = 4
CARD_EXTRA_HEIGHT = 10  # Some extra so we spill over visually a bit into the chevron
CARD_OUTER_MONO_BORDER_WIDTH = 2

OUTER_CORNER_RADIUS = 18
INNER_CORNER_RADIUS = 16
MENU_ITEM_CORNER_RADIUS = 13

MAX_PIN_LEN = 12

# TODO: Can we reference Display.HEIGHT here instead of 320?
CARD_CONTENT_HEIGHT_WITHOUT_HEADER = (
    320 - STATUSBAR_HEIGHT - CARD_CHEVRON_HEIGHT - CARD_PAD_BOTTOM) + CARD_EXTRA_HEIGHT
CARD_CONTENT_HEIGHT_WITH_HEADER = CARD_CONTENT_HEIGHT_WITHOUT_HEADER - CARD_HEADER_HEIGHT
MICRON_BAR_HEIGHT = 36

NUM_BACKUP_CODE_SECTIONS = 5
NUM_DIGITS_PER_BACKUP_CODE_SECTION = 4
TOTAL_BACKUP_CODE_DIGITS = NUM_BACKUP_CODE_SECTIONS * NUM_DIGITS_PER_BACKUP_CODE_SECTION

MAX_BACKUP_FILE_SIZE = const(10000)     # bytes

# Constants for legacy backup password
NUM_BACKUP_PASSWORD_WORDS = 6


# ==============================================
# External Flash Layout - Gen 1 (This firmware)
# ==============================================
# 1,792K  Firmware updates / PSBT signing buffer
#   128K  Flash cache
#   128K  User settings
# ==============================================
# 2,048K  Total external flash size
# ==============================================


def set_gen1_constants():
    # Only the differences are modified below
    global SPI_FLASH_TOTAL_SIZE, FLASH_CACHE_SIZE, FLASH_CACHE_START, FLASH_CACHE_END, FW_MAX_SIZE, PSBT_MAX_SIZE
    global FLASH_CACHE_SIZE_OLD, FLASH_CACHE_START_OLD, FLASH_CACHE_END_OLD
    global CARD_CONTENT_HEIGHT_WITHOUT_HEADER, CARD_CONTENT_HEIGHT_WITH_HEADER, CARD_PAD_BOTTOM, STATUSBAR_HEIGHT
    global OUTER_CORNER_RADIUS, CARD_PAD_LEFT, CARD_PAD_RIGHT, CARD_EXTRA_HEIGHT

    SPI_FLASH_TOTAL_SIZE = 2048 * 1024

    # Flash cache - fewer slots so that we can move user settings into external flash like Gen 1.2
    FLASH_CACHE_START = (USER_SETTINGS_START - FLASH_CACHE_SIZE)
    FLASH_CACHE_END = FLASH_CACHE_START + FLASH_CACHE_SIZE

    FLASH_CACHE_SIZE_OLD = 256 * 1024
    FLASH_CACHE_START_OLD = SPI_FLASH_TOTAL_SIZE - FLASH_CACHE_SIZE_OLD
    FLASH_CACHE_END_OLD = SPI_FLASH_TOTAL_SIZE

    # PSBT signing
    PSBT_MAX_SIZE = 1792 * 1024  # Total size available for both input and output

    # Display constants
    # TODO: Can we reference Display.HEIGHT here instead of 303?
    STATUSBAR_HEIGHT = 40
    CARD_PAD_BOTTOM = 28
    CARD_PAD_LEFT = 4
    CARD_PAD_RIGHT = 4
    OUTER_CORNER_RADIUS = 16
    CARD_EXTRA_HEIGHT = 14

    CARD_CONTENT_HEIGHT_WITHOUT_HEADER = (
        303 - STATUSBAR_HEIGHT - CARD_CHEVRON_HEIGHT - CARD_PAD_BOTTOM) + CARD_EXTRA_HEIGHT
    CARD_CONTENT_HEIGHT_WITH_HEADER = CARD_CONTENT_HEIGHT_WITHOUT_HEADER - CARD_HEADER_HEIGHT
