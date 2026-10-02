# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# QR messages must be fully displayable without changing the signed text.

import uasyncio as asyncio
from tasks.validate_electrum_message_task import validate_electrum_message_task


PATH = "m/44'/0'/0'/0/0"


async def validate(message):
    results = []

    async def on_done(value, error):
        results.append((value, error))

    await validate_electrum_message_task(on_done, 'signmessage {} ascii:{}'.format(PATH, message))
    assert len(results) == 1
    return results[0]


async def run_tests():
    # Printable ASCII, including markup and colons, reaches review unchanged.
    for message in (
        ''.join(chr(code) for code in range(32, 127)),
        'Visible #ffffff hidden text#',
        ' leading    spaces and trailing ',
        'message:with:colons',
    ):
        value, error = await validate(message)
        assert error is None
        assert value == (message, PATH)

    # NUL must not hide a signed suffix. Other controls (including LF and TAB),
    # DEL, and non-ASCII text are also outside the supported display charset.
    for character in tuple(chr(code) for code in range(32)) + ('\x7f', '\u00e9', '\u202e'):
        value, error = await validate('visible' + character + 'hidden')
        assert value is None
        assert error is not None


asyncio.run(run_tests())
return_value.write(b'OK')
