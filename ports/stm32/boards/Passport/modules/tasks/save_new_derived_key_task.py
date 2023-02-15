# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# save_new_derived_key_task.py - Task to save a new derived key


async def save_new_derived_key_task(on_done, index, key_name, key_type):
    from common import settings
    import stash
    from utils import get_derived_keys

    keys = get_derived_keys()
    has_passphrase = True if len(stash.bip39_passphrase) > 0 else False
    keys.append({'name': key_name, 'index': index, 'passphrase': has_passphrase, 'type': key_type})
    settings.set('derived_keys', keys)
    settings.save()
    # TODO: This can fail, so may need a try/except handler here
    await on_done(None)
