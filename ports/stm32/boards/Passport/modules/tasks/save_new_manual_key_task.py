# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# save_new_manual_key_task.py - Task to save a new derived key


async def save_new_manual_key_task(on_done, index, key_tn, key):
    from common import settings
    from utils import get_manual_keys
    from errors import Error

    keys = get_manual_keys()
    keys.append({'index': index, 'tn': key_tn, 'key': key})
    settings.set('manual_keys', keys)
    settings.save()
    await on_done(None)
