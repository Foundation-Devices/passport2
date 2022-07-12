
# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# write_data_to_file_task.py - Write data to microSD card at the given path.

from errors import Error
from files import CardSlot, CardMissingError


async def write_data_to_file_task(on_done, file_path, data):
    ''' NOTE: Assumes that that path above the leaf filename already exists.'''
    try:
        with CardSlot() as _card:
            with open(file_path, 'wb') as fd:
                fd.write(data)
                await on_done(None)

    except CardMissingError:
        await on_done(Error.MICROSD_CARD_MISSING)

    except Exception:
        await on_done(Error.FILE_WRITE_ERROR)
