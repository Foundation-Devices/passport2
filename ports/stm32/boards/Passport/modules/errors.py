# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# errors.py - Error codes that functions can return -- mostly used for tasks to return
#             errors to flows to avoid putting UI and strings into tasks.

from Enum import enum

Error = enum(
    'ADDRESS_NOT_FOUND',
    'CORRUPT_BACKUP_FILE',
    'FILE_READ_ERROR',
    'FILE_WRITE_ERROR',
    'INVALID_BACKUP_CODE',
    'INVALID_BACKUP_FILE_HEADER',
    'MICROSD_FORMAT_ERROR',
    'MICROSD_CARD_MISSING',
    'MULTISIG_STORAGE_IDX_ERROR'
    'NOT_BIP39_MODE',
    'OUT_OF_MEMORY_ERROR',
    'PSBT_FATAL_ERROR',
    'PSBT_FRAUDULENT_CHANGE_ERROR',
    'PSBT_INVALID',
    'SECURE_ELEMENT_ERROR',
    'USER_SETTINGS_FULL',
    'PSBT_TOO_LARGE',
)
