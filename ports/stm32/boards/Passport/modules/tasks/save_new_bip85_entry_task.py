# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# save_new_bip85_entry_task.py - Task to save a new BIP85 entry


async def save_new_bip85_entry_task(on_done, index, seed_name):
    from common import settings
    import stash
    from utils import get_bip85_records

    records = get_bip85_records()
    has_passphrase = True if len(stash.bip39_passphrase) > 0 else False
    records.append({'name': seed_name, 'index': index, 'passphrase': has_passphrase})
    settings.set('bip85_records', records)
    settings.save()
    # TODO: This can fail, so may need a try/except handler here
    await on_done(None)
