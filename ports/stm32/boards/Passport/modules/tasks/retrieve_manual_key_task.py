# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# retrieve_manual_key_task.py - Task to retrive a manual key from settings


async def retrieve_manual_key_task(on_done, index):
    from utils import get_manual_key_by_index

    key = get_manual_key_by_index(index)['key']
    await on_done(key, None)
