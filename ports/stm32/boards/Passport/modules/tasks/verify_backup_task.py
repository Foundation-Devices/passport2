# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# verify_backup_task.py - Task for verifying a backup from microSD.


import compat7z

from files import CardSlot, CardMissingError
from errors import Error
from constants import MAX_BACKUP_FILE_SIZE


async def verify_backup_task(on_done, backup_file_path):
    try:
        with CardSlot() as card:
            fd = open(backup_file_path, 'rb')

            try:
                try:
                    compat7z.check_file_headers(fd)
                except Exception as e:
                    await on_done(Error.INVALID_BACKUP_FILE_HEADER)
                    return

                zz = compat7z.Builder()
                files = zz.verify_file_crc(fd, MAX_BACKUP_FILE_SIZE)

                assert len(files) == 1
                fname, fsize = files[0]

            finally:
                fd.close()
    except CardMissingError:
        await on_done(Error.MICROSD_CARD_MISSING)
    except Exception as e:
        await on_done(Error.FILE_READ_ERRROR)

    await on_done(None)
