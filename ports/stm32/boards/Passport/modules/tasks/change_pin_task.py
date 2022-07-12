# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# change_pin_task.py - Task to change user's PIN

import common
from uasyncio import sleep_ms
from errors import Error


async def change_pin_task(on_done, old_pin, new_pin):
    pa = common.pa
    try:
        # print('change_pin_task(): old pin={}, new pin={}'.format(old_pin, new_pin))
        args = {}
        args['old_pin'] = (old_pin).encode()
        if isinstance(new_pin, (bytes, bytearray)):
            args['new_pin'] = new_pin
        else:
            args['new_pin'] = (new_pin).encode()
        pa.change(**args)
        # print('change_pin_task() SUCCESS!')
        await sleep_ms(2000)
        await on_done(True, None)
    except Exception as err:
        # print('change_pin_task(): ERROR: err={}'.format(err))
        await on_done(False, Error.SECURE_ELEMENT_ERROR)
