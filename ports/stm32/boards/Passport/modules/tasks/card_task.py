# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# card_task.py - Task for handling card flows

from uasyncio import CancelledError
import utils


async def card_task(card_desc):
    from common import ui

    try:
        flow = card_desc.get('flow')
        kwargs = card_desc.get('args', {})
        if flow is not None:
            # If this is an account card, then activate the account context
            account = card_desc.get('account')
            ui.set_active_account(account)

            ui.update_screen_info(card_desc)

            await flow(**kwargs).run()
    except CancelledError:
        # This is normal when switching cards
        pass
    except BaseException as exc:
        utils.handle_fatal_error(exc)
