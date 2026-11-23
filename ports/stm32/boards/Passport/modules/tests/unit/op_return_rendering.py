# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Rendering of OP_RETURN scriptPubKeys across push encodings and binary payloads.

from chains import BitcoinMain


def render(script):
    return BitcoinMain.render_address(script)


def must_fail(script):
    try:
        render(script)
    except ValueError:
        return

    raise RuntimeError('expected ValueError for {}'.format(script))


# Every standard single-push encoding renders the same payload.
assert render(b'\x6a\x05hello') == 'OP_RETURN:\nhello'          # direct push
assert render(b'\x6a\x4c\x05hello') == 'OP_RETURN:\nhello'      # OP_PUSHDATA1
assert render(b'\x6a\x4d\x05\x00hello') == 'OP_RETURN:\nhello'  # OP_PUSHDATA2

# A direct push of the largest size still takes its length from the opcode.
assert render(b'\x6a\x4b' + (b'a' * 0x4b)) == 'OP_RETURN:\n{}'.format('a' * 0x4b)

# Bare OP_RETURN carries no payload, but must keep the newline that
# render_output() relies on to split the message body off the prefix.
bare = render(b'\x6a')
assert bare == 'OP_RETURN:\n'
assert bare.startswith('OP_RETURN')
assert bare.split('\n', 1)[1] == ''

# Payloads that aren't valid UTF-8 are shown as hex instead of aborting the render.
assert render(b'\x6a\x04\xff\xfe\xfd\xfc') == 'OP_RETURN:\nfffefdfc'
assert render(b'\x6a\x4c\x04\xff\xfe\xfd\xfc') == 'OP_RETURN:\nfffefdfc'

# A declared push size that disagrees with the script length is not rendered.
must_fail(b'\x6a\x05hell')
must_fail(b'\x6a\x05helloX')
must_fail(b'\x6a\x4c\x05hell')
must_fail(b'\x6a\x4d\x05\x00hell')

# Truncated push headers.
must_fail(b'\x6a\x4c')
must_fail(b'\x6a\x4d\x05')

# Encodings we don't render, and scripts that aren't OP_RETURN at all.
must_fail(b'\x6a\x4e\x05\x00\x00\x00hello')  # OP_PUSHDATA4
must_fail(b'\x6a\x00')
must_fail(b'\x00\x01\x02')

return_value.write(b'OK')
