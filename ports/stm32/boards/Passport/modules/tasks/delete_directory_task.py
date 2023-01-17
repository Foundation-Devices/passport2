# SPDX-FileCopyrightText: 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# delete_directory_task.py - Task to delete a directory recursively


async def delete_directory_task(on_done, full_path):
    from utils import get_file_list, delete_file
    from uasyncio import sleep_ms

    subfiles = get_file_list(path=full_path, include_folders=True)

    while len(subfiles) != 0:
        for f in subfiles:
            (name, path, folder) = f
            if folder:
                subsubfiles = get_file_list(path=path, include_folders=True)
                if len(subsubfiles) == 0:
                    delete_file(path)
                    subfiles.remove(f)
                else:
                    subfiles.extend(subsubfiles)
            else:
                delete_file(path)
                subfiles.remove(f)

            await sleep_ms(1)

    delete_file(full_path)
    await on_done(None)
