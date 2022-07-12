# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# save_backup_task.py - Task for backing up Passport to microSD.

import gc
import compat7z
from files import CardSlot, CardMissingError
from errors import Error
from utils import get_backup_code_as_password, xfp2str, get_backups_folder_path, ensure_folder_exists, file_exists
from export import render_backup_contents
from errors import Error


async def save_backup_task(on_done, on_progress, backup_code):
    from common import settings

    # Pre-flight check for microSD
    try:
        with CardSlot() as card:
            pass
    except CardMissingError:
        await on_done(Error.MICROSD_CARD_MISSING)
        return

    body = render_backup_contents().encode()

    backup_num = 1
    xfp = xfp2str(settings.get('xfp')).lower()
    # print('XFP: {}'.format(xfp))

    gc.collect()
    if backup_code is None:
        await on_done(Error.INVALID_BACKUP_CODE)

    password = get_backup_code_as_password(backup_code)
    # print('\n\n>>>>>>>>>>>>>>> Password:  {}\n\n'.format(password))

    zz = compat7z.Builder(password=password, progress_fcn=on_progress)
    zz.add_data(body)

    hdr, footer = zz.save('passport-backup.txt')

    del body

    gc.collect()

    while True:
        base_filename = ''

        try:
            with CardSlot() as card:
                backups_path = get_backups_folder_path()
                ensure_folder_exists(backups_path)

                # Make a unique filename
                while True:
                    base_filename = '{}-backup-{}.7z'.format(xfp, backup_num)
                    fname = '{}/{}'.format(backups_path, base_filename)

                    # Ensure filename doesn't already exist
                    if not file_exists(fname):
                        break

                    # Ooops...that exists, so increment and try again
                    backup_num += 1

                # print('Saving to fname={}'.format(fname))

                # Do actual write
                with open(fname, 'wb') as fd:
                    if zz:
                        fd.write(hdr)
                        fd.write(zz.body)
                        fd.write(footer)
                    else:
                        fd.write(body)

            await on_done(None)
            return

        except CardMissingError:
            await on_done(Error.MICROSD_CARD_MISSING)
            return
        except Exception as e:
            # print("Exception: {}".format(e))
            await on_done(Error.FILE_WRITE_ERROR)
            return
