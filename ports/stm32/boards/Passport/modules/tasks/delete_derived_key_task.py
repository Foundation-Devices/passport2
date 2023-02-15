# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# delete_derived_key_task.py - Task to delete a derived key

from utils import get_derived_keys


async def delete_derived_key_task(on_done, key):
    from common import settings

    keys = get_derived_keys()
    # Rename to an empty string, so indices will still be tracked
    keys.remove(key)
    key['name'] = ''
    keys.append(key)
    settings.set('derived_keys', keys)
    settings.save()

    await on_done(None)
