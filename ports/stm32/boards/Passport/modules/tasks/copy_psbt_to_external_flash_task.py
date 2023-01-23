# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# copy_psbt_to_external_flash_task.py - Task to perform the copy to flash and provide progress updates

from public_constants import MAX_TXN_LEN


async def copy_psbt_to_external_flash_task(on_done, on_progress, data, offset):
    # sign a PSBT file found on a microSD card
    from uio import BytesIO
    from passport import sram4
    from sffile import SFFile
    from errors import Error
    from utils import HexStreamer, Base64Streamer, HexWriter, Base64Writer

    # copy buffer into external SPI Flash
    # - accepts hex or base64 encoding, but binary prefered
    with BytesIO(data) as fd:
        # See how long it is -- This version of seek returns the final offset
        psbt_len = len(data)

        if psbt_len > MAX_TXN_LEN:
            await on_done(0, None, Error.PSBT_INVALID)
            return

        # determine encoding used, although we prefer binary
        taste = fd.read(10)
        fd.seek(0)

        if taste[0:5] == b'psbt\xff':
            decoder = None

            def output_encoder(x):
                return x
        elif taste[0:10] == b'70736274ff':
            decoder = HexStreamer()
            output_encoder = HexWriter
            psbt_len //= 2
        elif taste[0:6] == b'cHNidP':
            decoder = Base64Streamer()
            output_encoder = Base64Writer
            psbt_len = (psbt_len * 3 // 4) + 10
        else:
            await on_done(0, None, Error.PSBT_INVALID)
            return

        total = 0
        with SFFile(offset, max_size=psbt_len) as out:
            # blank flash
            await out.erase()

            while 1:
                n = fd.readinto(sram4.tmp_buf)
                # print('sign copy to SPI flash 1: n={}'.format(n))
                if not n:
                    break

                if n == len(sram4.tmp_buf):
                    abuf = sram4.tmp_buf
                else:
                    abuf = memoryview(sram4.tmp_buf)[0:n]

                if not decoder:
                    out.write(abuf)
                    total += n
                else:
                    for here in decoder.more(abuf):
                        out.write(here)
                        total += len(here)

                # print('sign copy to SPI flash 2: {}/{} = {}'.format(total, psbt_len, total/psbt_len))

        # Might have been whitespace inflating initial estimate of PSBT size
        if total > psbt_len:
            await on_done(0, output_encoder, Error.PSBT_INVALID)
            return

        await on_done(psbt_len, output_encoder, None)
