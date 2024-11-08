# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# delete_account_task.py - Task to delete an account

from utils import get_accounts


async def delete_account_task(on_done, account_num, xfp):
    from common import settings

    accounts = get_accounts()
    accounts = list(filter(lambda acct: (acct.get('acct_num') != account_num or acct.get('xfp') != xfp), accounts))
    settings.set('accounts', accounts)
    settings.save()

    await on_done(None)
