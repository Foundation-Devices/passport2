# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# save_wallet_export_to_microsd_task.py - Task to save the given wallet data to microsd

from files import CardSlot, CardMissingError
from errors import Error


async def save_wallet_export_to_microsd_task(on_done, filename, data):
    try:
        with CardSlot() as card:
            # Write the data
            with open(filename, 'wb') as fd:
                fd.write(data)

    except CardMissingError:
        await on_done(Error.MICROSD_CARD_MISSING)
    except Exception as e:
        # print("save_wallet_export_to_microsd_task(): Exception: {}".format(e))
        await on_done(Error.FILE_WRITE_ERROR)
