# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# save_new_derived_key_task.py - Task to save a new derived key


async def save_new_derived_key_task(on_done, index, key_name, key_tn, xfp):
    from common import settings
    from utils import get_derived_keys

    keys = get_derived_keys()
    keys.append({'name': key_name,
                 'index': index,
                 'tn': key_tn,
                 'xfp': xfp,
                 'hidden': False})
    settings.set('derived_keys', keys)
    settings.save()
    # TODO: This can fail, so may need a try/except handler here
    await on_done(None)
