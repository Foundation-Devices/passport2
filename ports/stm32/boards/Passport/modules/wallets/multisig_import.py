# SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# multisig_import.py - Multisig config import


# TODO: Consider refactoring these functions with import_mulitisig_wallet_from_qr_flow.py and
#       import_mulitisig_wallet_from_microsd_flow.py.  These functions are called from
#       connect_wallet_flow.py, and that probably needs to be modified during the refactoring.

async def read_multisig_config_from_qr():
    from pages import ScanQRPage
    return await ScanQRPage().show()


async def read_multisig_config_from_microsd():
    from flows import FilePickerFlow
    from pages import InsertMicroSDPage, ErrorPage
    from tasks import read_file_task
    from utils import spinner_task
    from errors import Error

    result = await FilePickerFlow(show_folders=True).run()
    if result is None:
        return None

    while True:
        _filename, full_path, is_folder = result
        if not is_folder:
            result = await spinner_task(
                'Reading File',
                read_file_task,
                args=[full_path])
            (data, error) = result
            if error is None:
                # print('data read from file="{}"'.format(data))
                return data

            elif error is Error.MICROSD_CARD_MISSING:
                result = await InsertMicroSDPage().show()
                if not result:
                    return None
                else:
                    # Loop around and retry
                    continue

            elif error is Error.FILE_WRITE_ERROR:
                await ErrorPage(text='Unable to read multisig config file from microSD card.').show()
                return None
