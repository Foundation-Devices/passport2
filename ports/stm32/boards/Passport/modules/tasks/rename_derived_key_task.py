# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# rename_derived_key_task.py - Task to rename a derived key

from utils import get_derived_keys


async def rename_derived_key_task(on_done, key, new_name):
    from common import settings

    keys = get_derived_keys()
    keys.remove(key)
    key['name'] = new_name
    keys.append(key)
    settings.set('derived_keys', keys)
    settings.save()

    await on_done(None)
