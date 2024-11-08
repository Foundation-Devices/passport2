# SPDX-FileCopyrightText: © 2024 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# validate_electrum_message_task.py - Task to parse and validate an electrum message for signing

from utils import validate_sign_text


async def validate_electrum_message_task(on_done, message):
    try:
        parts = message.split(':', 1)
        message = parts[1]
        header_elements = parts[0].split(' ')

        if len(header_elements) != 3:
            await on_done(None, 'Message format must be "signmessage {derivation_path} ascii:{message}"')
            return

        if header_elements[0] != 'signmessage':
            await on_done(None, 'Not a valid message to sign')
            return

        if header_elements[2] != 'ascii':
            await on_done(None, 'Unsupported message type')
            return

        (subpath, error) = validate_sign_text(message,
                                              header_elements[1],
                                              space_limit=False,
                                              check_whitespace=False,
                                              check_ascii=False)

        if error:
            await on_done(None, error)
            return

        await on_done((message, subpath), None)
        return

    except Exception as e:
        await on_done(None, 'Invalid message format')
        return
