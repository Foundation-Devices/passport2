# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# apply_passphrase_task.py - Task to apply a passphrase

from errors import Error
import stash
import foundation
from utils import bytes_to_hex_str
import common


async def apply_passphrase_task(on_done, passphrase):
    if stash.bip39_passphrase == '':
        # This checks if the root_xfp has been generated and saved,
        # If not, it's saved to settings for future use
        common.settings.get('root_xfp')

    stash.bip39_passphrase = passphrase

    # Create a hash from the passphrase
    if len(stash.bip39_passphrase) > 0:
        digest = bytearray(32)
        foundation.sha256(stash.bip39_passphrase, digest)
        digest_hex = bytes_to_hex_str(digest)
        stash.bip39_hash = digest_hex[:8]  # Take first 8 characters (32-bits)
        # print('stash.bip39_hash={}'.format(stash.bip39_hash))
    else:
        stash.bip39_hash = ''

    with stash.SensitiveValues() as sv:
        if sv.mode != 'words':
            # can't do it without original seed words
            assert('No BIP39 seed words')
            await on_done(Error.NOT_BIP39_MODE)
            return

        sv.capture_xpub()

    await on_done(None)
