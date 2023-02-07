# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# save_new_account_task.py - Task to save a new account

from utils import get_accounts


async def save_new_account_task(on_done, account_num, account_name):
    from common import settings

    accounts = get_accounts()
    accounts.append({'name': account_name, 'acct_num': account_num})
    settings.set('accounts', accounts)
    settings.save()
    # TODO: This can fail, so may need a try/except handler here
    await on_done(None)
