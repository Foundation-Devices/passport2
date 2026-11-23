# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundation.xyz>
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
        import stash
        from utils import get_backup_code_as_password
        from export import render_backup_contents

        body = render_backup_contents().encode()
        zz = None
        try:
            password = get_backup_code_as_password(self.backup_code)
            zz = compat7z.Builder(password=password)
            zz.add_data(body)
            hdr, footer = zz.save('passport-backup.txt')
        finally:
            # Neither the plaintext nor the key is needed once encrypted.
            # str.encode() shares the string's buffer, so this also clears the
            # rendered text. That text holds this device's secrets, so it is
            # never an interned string that other code shares.
            stash.blank_object(body)
            if zz is not None:
                zz.wipe_key()
        del body
        gc.collect()

        with open(filename, 'wb') as fd:
            fd.write(hdr)
            fd.write(zz.body)
            fd.write(footer)
