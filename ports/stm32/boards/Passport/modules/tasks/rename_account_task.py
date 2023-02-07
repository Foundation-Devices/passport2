# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# rename_account_task.py - Task to rename and save an account

from utils import get_accounts


async def rename_account_task(on_done, account_num, account_name):
    from common import settings

    accounts = get_accounts()
    for account in accounts:
        if account.get('acct_num') == account_num:
            account['name'] = account_name
            break

    settings.set('accounts', accounts)
    settings.save()

    await on_done(None)
