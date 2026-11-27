# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# login_task.py - Task to login the user

import common
import passport
from uasyncio import sleep_ms
from pincodes import BootloaderError
import stash
from utils import has_seed


async def login_task(on_done, pin):
    # Sleep at least 4ms which is the rate at which the background thread will run.
    await sleep_ms(4)
    # print('login_task started!!!  pin: {}'.format(pin))
    pa = common.pa

    try:
        # print('login_task started!!!  2')
        if passport.IS_SIMULATOR:
            await sleep_ms(1000)

        pa.setup(pin)
        if pa.login():
            # PIN is correct!

            # TODO: Passphrase handling
            # enable_passphrase = settings.get('enable_passphrase', False)
            # if enable_passphrase:
            #     self.goto(self.ENTER_PASSPHRASE)
            # else:
            #     return
            # print('PIN is correct!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!11')

            # This should run once on devices that don't have the xfp saved to flash
            if has_seed() and (common.settings.current.get('xfp', None) is None or
                               common.settings.current.get('xpub', None) is None):
                with stash.SensitiveValues() as sv:
                    sv.capture_xpub(save=True)
            await on_done(True, None)

    except BootloaderError as err:
        # print('BootloaderError {}'.format(err))
        await on_done(False, err)
    except RuntimeError as err:
        # print('RuntimeError {}'.format(err))
        await on_done(False, err)
    except Exception as err:
        # print('Exception {}'.format(err))
        await on_done(False, err)
