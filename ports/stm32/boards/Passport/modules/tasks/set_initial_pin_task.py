# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# set_initial_pin_task.py - Task to set the initial PIN

import common


async def set_initial_pin_task(on_done, new_pin):
    pa = common.pa
    try:
        # print('set_initial_pin_task(): new pin={}'.format(new_pin))
        if not pa.is_blank():
            await on_done(False, 'PIN already set')
            return

        pa.change(new_pin=new_pin)

        pa.setup(new_pin)
        result = pa.login()
        # print('set_initial_pin_task() SUCCESS? {}'.format(result))

        await on_done(result, None)

    except Exception as err:
        # print('set_initial_pin_task(): ERROR: err={}'.format(err))
        # await sleep_ms(1000)
        await on_done(False, err)
