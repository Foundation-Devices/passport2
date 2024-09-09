# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# get_backup_code_task.py - Task to get the backup code for the current device/wallet.

import trezorcrypto
from micropython import const
from utils import has_temporary_seed

# we make passwords with this number of words
_NUM_DECIMAL_DIGITS_IN_BACKUP_CODE = const(20)

# Number of digits to extract from each 32-bit value
_NUM_DECIMAL_DIGITS_PER_32_BIT_UINT = const(4)

_NUM_ITERATIONS = const(_NUM_DECIMAL_DIGITS_IN_BACKUP_CODE // _NUM_DECIMAL_DIGITS_PER_32_BIT_UINT)


def get_backup_code():
    from common import system, pa, settings

    device_hash = bytearray(32)
    system.get_device_hash(device_hash)
    if has_temporary_seed():
        secret = settings.get('temporary_seed')
    else:
        secret = pa.fetch()
    # print('secret: {}'.format(bytes_to_hex_str(secret)))

    hash = trezorcrypto.sha256()
    hash.update(device_hash)
    hash.update(secret)
    backup_hash = hash.digest()

    from utils import bytes_to_hex_str
    # print('backup_hash: {}'.format(bytes_to_hex_str(backup_hash)))

    backup_code = []
    for i in range(_NUM_ITERATIONS):
        curr_value = int.from_bytes(backup_hash[i * 4:(i + 1) * 4], 'big')
        for d in range(_NUM_DECIMAL_DIGITS_PER_32_BIT_UINT):
            digit = curr_value % 10
            curr_value = curr_value // 10
            backup_code.insert(0, digit)

    return backup_code


async def get_backup_code_task(on_done):
    import passport
    backup_code = get_backup_code()

    if passport.IS_SIMULATOR:
        # Short delay in simulator to simulate SE and hash time
        from uasyncio import sleep_ms
        await sleep_ms(1000)

    await on_done(backup_code, None)
