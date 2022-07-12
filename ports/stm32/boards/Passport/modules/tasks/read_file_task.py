# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# read_file_task.py - Write data to microSD card at the given path.

from errors import Error
from files import CardSlot, CardMissingError


async def read_file_task(on_done, file_path):
    ''' NOTE: Assumes that that path above the leaf filename already exists.'''
    try:
        with CardSlot() as _card:
            with open(file_path, 'rb') as fd:
                data = fd.read()
                await on_done(data, None)

    except CardMissingError:
        await on_done(None, Error.MICROSD_CARD_MISSING)

    except Exception:
        await on_done(None, Error.FILE_READ_ERROR)
