# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# custom_microsd_write_task.py - Use a custom function to writte to the microsd.


async def custom_microsd_write_task(on_done, filename, write_fn):
    from files import CardMissingError
    from errors import Error

    try:
        write_fn(filename)
    except CardMissingError:
        await on_done(Error.MICROSD_CARD_MISSING)
        return
    except Exception as e:
        await on_done(Error.FILE_WRITE_ERROR)
        return
    await on_done(None)
