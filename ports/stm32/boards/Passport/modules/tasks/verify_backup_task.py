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


from backup_reader import verify_backup_file


async def verify_backup_task(on_done, decryption_password, backup_file_path):
    error = verify_backup_file(decryption_password, backup_file_path)
    await on_done(error)
