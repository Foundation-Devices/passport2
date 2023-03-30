# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# backup_common_flow.py - Save a backup to microSD

from flows import SaveToMicroSDFlow


class BackupCommonFlow(SaveToMicroSDFlow):
    def __init__(self, backup_code, automatic=False):
        from utils import xfp2str, get_backups_folder_path
        from common import settings

        xfp = xfp2str(settings.get('root_xfp')).lower()
        filename = '{}-backup.7z'.format(xfp)
        path = get_backups_folder_path() + '/'
        self.backup_code = backup_code
        super().__init__(filename=filename,
                         path=path,
                         write_task=self.write_task,
                         success_text="backup")

    async def write_task(self, on_done, filename):
        import gc
        import compat7z
        from utils import get_backup_code_as_password
        from export import render_backup_contents
        from files import CardMissingError
        from errors import Error

        body = render_backup_contents().encode()
        password = get_backup_code_as_password(self.backup_code)
        print(password)
        zz = compat7z.Builder(password=password)
        zz.add_data(body)
        hdr, footer = zz.save('passport-backup.txt')
        del body
        gc.collect()
        try:
            with open(filename, 'wb') as fd:
                if zz:
                    fd.write(hdr)
                    fd.write(zz.body)
                    fd.write(footer)
                else:
                    fd.write(body)
        except CardMissingError:
            await on_done(Error.MICROSD_CARD_MISSING)
            return
        except Exception as e:
            await on_done(Error.FILE_WRITE_ERROR)
            return
        await on_done(None)
