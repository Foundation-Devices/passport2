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
from ubinascii import b2a_base64
from public_constants import AF_P2TR
from utils import sign_message_digest_recoverable


async def sign_text_file_task(on_done, text, subpath, addr_fmt, expected_address=None, bip322_request=None):
    # With a BIP-322 request read from a PSBT, the result is that PSBT, signed, instead of a text signature.

    with stash.SensitiveValues() as sv:
        node = sv.derive_path(subpath)
        address = sv.chain.address(node, addr_fmt)

    if expected_address is not None and address != expected_address:
        await on_done(None, None, 'Address mismatch: expected {}, got {}'.format(expected_address, address))
        return

    message = text.encode()
    if addr_fmt == AF_P2TR:
        from bip322 import sign_taproot_request, sign_taproot_simple

        try:
            with stash.SensitiveValues() as sv:
                node = sv.derive_path(subpath)
                private_key = node.private_key()
                sv.register(private_key)
                if bip322_request is None:
                    signature = sign_taproot_simple(message, node.public_key()[1:], private_key)
                else:
                    signature = sign_taproot_request(bip322_request, node.public_key()[1:], private_key)
        except ValueError as e:
            await on_done(None, None, str(e))
            return
    elif bip322_request is not None:
        await on_done(None, None, 'BIP-322 requests can only be signed for Taproot addresses')
        return
    else:
        digest = chains.current_chain().hash_message(message)
        raw_signature = sign_message_digest_recoverable(digest, subpath)
        signature = b2a_base64(raw_signature).decode('ascii').strip()

    await on_done(signature, address, None)
