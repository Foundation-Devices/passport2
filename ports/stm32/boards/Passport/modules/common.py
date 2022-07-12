# SPDX-FileCopyrightText: 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# common.py - Shared global values

# Get the async event loop to pass in where needed
from animations.constants import TRANSITION_DIR_REPLACE
import utime
loop = None

# System
system = None

# Keypad
keypad = None

# Internal flash-based settings
settings = None

# External SPI flash cache
flash_cache = None

# Display
display = None

# UI
ui = None

# PinAttempts
pa = None

# External SPI Flash
sf = None

# Avalanche noise source
noise = None

# Demo
demo_active = False
demo_count = 0

# Last time the user interacted (i.e., pressed/released any key)
last_activity_time = utime.ticks_ms()

# Screenshot mode
screenshot_mode_enabled = False

# Snapshot mode
snapshot_mode_enabled = False

# Power monitor
powermon = None

# Battery Monitor
enable_battery_mon = False

# Active account
active_account = None

# Multisig wallet to associate with New Account flow
new_multisig_wallet = None
is_new_wallet_a_duplicate = False

# The QRType of the last QR code that was scanned
last_scanned_qr_type = None
last_scanned_ur_prefix = None

# Cached Developer PubKey
cached_pubkey = None

is_old_gen12_dev_board = False

# Input Device for keypad for LVGL
keypad_indev = None

is_dark_theme = True

# Custom events id dict
custom_events = {}

# What type of transition should be done for the next page transition?
page_transition_dir = TRANSITION_DIR_REPLACE

# What type of transition should be done for the next card transition?
card_transition_dir = TRANSITION_DIR_REPLACE
