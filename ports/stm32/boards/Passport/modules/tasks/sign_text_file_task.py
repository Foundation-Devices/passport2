# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# sign_text_file_task.py - Sign the specified file

import stash
import chains
from utils import sign_message_digest_recoverable


async def sign_text_file_task(on_done, text, subpath, addr_fmt, expected_address=None):

    with stash.SensitiveValues() as sv:
        node = sv.derive_path(subpath)
        address = sv.chain.address(node, addr_fmt)

    if expected_address is not None and address != expected_address:
        await on_done(None, None, 'Address mismatch: expected {}, got {}'.format(expected_address, address))
        return

    digest = chains.current_chain().hash_message(text.encode())
    # signature will be 65 bytes
    signature = sign_message_digest_recoverable(digest, subpath)

    await on_done(signature, address, None)
