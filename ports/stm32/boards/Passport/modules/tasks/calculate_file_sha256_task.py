# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# calculate_file_sha256_task.py - Read a file chunk by chunk and calculate it's sha256

import math
import trezorcrypto
from files import CardSlot, CardMissingError
from utils import B2A, get_filesize
from uasyncio import sleep_ms
from errors import Error

_CHUNK_SIZE = const(2048)


async def calculate_file_sha256_task(file_path, on_progress, on_done):
    chk = trezorcrypto.sha256()

    try:
        with CardSlot() as _card:

            size = get_filesize(file_path)
            num_parts = math.ceil(size / _CHUNK_SIZE)

            with open(file_path, 'rb') as fp:
                part_num = 0
                last_percent = -1
                bytes_read = 0
                while True:
                    data = fp.read(_CHUNK_SIZE)
                    if not data:
                        if bytes_read == size:
                            break
                        else:
                            await on_done(None, Error.FILE_READ_ERROR)
                            return

                    bytes_read += len(data)
                    part_num += 1

                    chk.update(data)

                    percent = int((part_num / num_parts) * 100)
                    if percent != last_percent:
                        last_percent = percent
                        on_progress(percent)
                        await sleep_ms(1)

    except CardMissingError:
        await on_done(None, Error.MICROSD_CARD_MISSING)
        return
    except Exception as e:
        await on_done(None, Error.FILE_READ_ERROR)
        return

    # Calculate the digests and convert it to a string
    digest = B2A(chk.digest())

    await on_done(digest, None)
