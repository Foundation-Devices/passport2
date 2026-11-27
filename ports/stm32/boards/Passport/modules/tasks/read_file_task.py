# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# read_file_task.py - Write data to microSD card at the given path.

from errors import Error
from files import CardSlot, CardMissingError


def default_read_fn(fd):
    return fd.read()


async def read_file_task(on_done, file_path, binary=True, read_fn=None):
    ''' NOTE: Assumes that that path above the leaf filename already exists.'''
    mode = 'b' if binary else ''
    read_fn = read_fn or default_read_fn
    try:
        with CardSlot() as _card:
            with open(file_path, 'r' + mode) as fd:
                data = read_fn(fd)
                await on_done(data, None)

    except CardMissingError:
        await on_done(None, Error.MICROSD_CARD_MISSING)

    except Exception:
        await on_done(None, Error.FILE_READ_ERROR)
