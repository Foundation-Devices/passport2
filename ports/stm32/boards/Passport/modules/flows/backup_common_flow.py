# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# backup_common_flow.py - Save a backup to microSD

from flows.save_to_microsd_flow import SaveToMicroSDFlow


class BackupCommonFlow(SaveToMicroSDFlow):
    def __init__(self, backup_code, automatic=False):
        from utils import xfp2str, get_backups_folder_path
        from common import settings

        xfp = xfp2str(settings.get('root_xfp')).lower()
        filename = '{}-backup.7z'.format(xfp)
        path = get_backups_folder_path()
        self.backup_code = backup_code
        super().__init__(filename=filename,
                         path=path,
                         write_fn=self.write_fn,
                         success_text="backup",
                         automatic=automatic)

    def write_fn(self, filename):
        import gc
        import compat7z
        from utils import get_backup_code_as_password
        from export import render_backup_contents

        body = render_backup_contents().encode()
        password = get_backup_code_as_password(self.backup_code)
        zz = compat7z.Builder(password=password)
        zz.add_data(body)
        hdr, footer = zz.save('passport-backup.txt')
        del body
        gc.collect()

        with open(filename, 'wb') as fd:
            if zz:
                fd.write(hdr)
                fd.write(zz.body)
                fd.write(footer)
            else:
                fd.write(body)
