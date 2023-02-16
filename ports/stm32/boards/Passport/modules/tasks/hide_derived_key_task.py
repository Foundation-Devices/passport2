# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# hide_derived_key_task.py - Task to hide a derived key

from utils import get_derived_keys


async def hide_derived_key_task(on_done, key, hidden):
    from common import settings

    keys = get_derived_keys()
    keys.remove(key)
    key['hidden'] = hidden
    keys.append(key)
    settings.set('derived_keys', keys)
    settings.save()

    await on_done(None)
