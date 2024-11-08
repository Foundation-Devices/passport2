# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# rename_account_task.py - Task to rename and save an account

from utils import get_accounts


async def rename_account_task(on_done, account_num, account_name, xfp):
    from common import settings

    accounts = get_accounts()
    for account in accounts:
        if account.get('acct_num') == account_num and account.get('xfp') == xfp:
            account['name'] = account_name
            break
    else:
        # If account wasn't found, it's likely an unsaved default account being renamed
        accounts.append({'acct_num': account_num, 'name': account_name, 'xfp': xfp})

    settings.set('accounts', accounts)
    settings.save()

    await on_done(None)
