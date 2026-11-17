# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# validate_bip322_request_task.py - Task to read and validate a BIP-322 message request sent as a PSBT

from utils import keypath_to_str, swab32, validate_sign_text


async def validate_bip322_request_task(on_done, psbt):
    import stash
    from bip322 import TAPROOT_ONLY, read_signing_request
    from common import settings
    from public_constants import AF_P2TR
    from taproot import output_script
    from wallets.utils import get_addr_type_from_deriv

    try:
        request = read_signing_request(psbt)
    except ValueError as e:
        await on_done(None, str(e))
        return

    try:
        message = str(request.message, 'utf-8')
    except UnicodeError:
        await on_done(None, 'Message is not valid text.')
        return

    xfp = settings.get('xfp', 0)
    if request.xfp != xfp and request.xfp != swab32(xfp):
        await on_done(None, 'This message request is for a different wallet.')
        return

    # Same checks as a message scanned as text.
    (subpath, error) = validate_sign_text(message, keypath_to_str([request.xfp] + request.path),
                                          space_limit=False, check_whitespace=False, allow_newlines=True)
    if error:
        await on_done(None, error)
        return

    # The review shows the address this path derives, so it must be the Taproot address that signs.
    if get_addr_type_from_deriv(subpath) != AF_P2TR:
        await on_done(None, TAPROOT_ONLY)
        return

    with stash.SensitiveValues() as sv:
        node = sv.derive_path(subpath)
        matches = output_script(node.public_key()[1:], None) == request.script_pubkey

    if not matches:
        await on_done(None, 'The address in this request does not match its derivation path.')
        return

    await on_done((message, subpath, request), None)
