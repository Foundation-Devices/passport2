# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# restore_backup_task.py - Task for restoring Passport from a microSD backup file.

import chains
import compat7z
import stash
import ujson

from files import CardSlot, CardMissingError
from ubinascii import unhexlify as a2b_hex
from errors import Error
from constants import MAX_BACKUP_FILE_SIZE
from pincodes import SE_SECRET_LEN


async def restore_backup_task(on_done, decryption_password, backup_file_path):
    from common import pa, settings

    try:
        with CardSlot() as card:
            fd = open(backup_file_path, 'rb')

            try:
                try:
                    compat7z.check_file_headers(fd)
                except Exception as e:
                    await on_done(Error.INVALID_BACKUP_FILE_HEADER)
                    return

                try:
                    zz = compat7z.Builder()
                    fname, contents = zz.read_file(fd, decryption_password, MAX_BACKUP_FILE_SIZE,
                                                   progress_fcn=None)

                    # Quick sanity check
                    assert contents[0:1] == b'#' and contents[-1:] == b'\n'

                except Exception as e:
                    # Assume all exceptions here are "incorrect password" errors
                    await on_done(Error.INVALID_BACKUP_CODE)
                    return

            finally:
                fd.close()

    except CardMissingError:
        await on_done(Error.MICROSD_CARD_MISSING)
        return
    except BaseException:
        await on_done(Error.FILE_READ_ERROR)
        return

    vals = {}
    for line in contents.decode().split('\n'):
        if not line:
            continue
        if line[0] == '#':
            continue

        try:
            k, v = line.split(' = ', 1)
            # print("%s = %s" % (k, v))

            vals[k] = ujson.loads(v)
        except BaseException:
            # print("Unable to decode line: %r" % line)
            # Keep going to give user the best chance to restore
            pass

    # Now restore the secret
    try:
        chain = chains.get_chain(vals.get('chain', 'BTC'))

        if 'raw_secret' not in vals:
            await on_done(Error.CORRUPT_BACKUP_FILE)
            return

        raw = bytearray(SE_SECRET_LEN)
        rs = vals.pop('raw_secret')
        if len(rs) % 2:
            rs += '0'
        x = a2b_hex(rs)
        raw[0:len(x)] = x

        # Check that we can decode this right (might be different firmware)
        opmode, bits, node = stash.SecretStash.decode(raw)
        if not node:
            await on_done(Error.CORRUPT_BACKUP_FILE)
            return

        # Cerify against xprv value (if we have it)
        if 'xprv' in vals:
            check_xprv = chain.serialize_private(node)
            if check_xprv != vals['xprv']:
                await on_done(Error.CORRUPT_BACKUP_FILE)
                return

    except Exception as e:
        await on_done(Error.CORRUPT_BACKUP_FILE)
        return

    # Set the secret into the Secure Element
    pa.change(new_secret=raw)

    # Force the right chain and update XFP & XPUB
    await pa.new_main_secret(raw, chain)

    # Finally, restore the settings
    for idx, k in enumerate(vals):
        if not k.startswith('setting.'):
            continue

        if k == 'xfp' or k == 'xpub':
            continue

        settings.set(k[8:], vals[k])

    # Success!
    await on_done(None)
