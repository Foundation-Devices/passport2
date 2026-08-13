# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# verify_backup_task.py - Task for verifying a backup from microSD.


import gc

from backup_reader import read_backup_file


async def verify_backup_task(on_done, decryption_password, backup_file_path):
    contents, error = read_backup_file(decryption_password, backup_file_path)

    # Verification only needs the successful integrity result. Do not retain
    # decrypted backup contents after the reader has validated them.
    contents = None
    gc.collect()

    await on_done(error)
