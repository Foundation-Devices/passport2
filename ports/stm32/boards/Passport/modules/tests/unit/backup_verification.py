# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Exercise backup encryption and validation using the simulator's MicroPython
# crypto implementation.

import compat7z

from uio import BytesIO


PASSWORD = '1111-2222-3333-4444-5555'
CONTENTS = b'#' + (b'a' * 30) + b'\n'
MAX_SIZE = 1024


def expect_failure(operation):
    try:
        operation()
    except Exception:
        return
    assert False


def validate(archive, password=PASSWORD, max_size=MAX_SIZE):
    fd = BytesIO(archive)
    compat7z.check_file_headers(fd)
    return compat7z.Builder().read_file(fd, password, max_size, progress_fcn=None)


# Avoid touching simulator device state while generating the fixture.
compat7z.urandom = lambda length: bytes(range(length))

builder = compat7z.Builder(password=PASSWORD)
builder.add_data(CONTENTS)
prefix, footer = builder.save('passport-backup.txt')
archive = prefix + builder.body + footer

filename, plaintext = validate(archive)
assert filename == 'passport-backup.txt'
assert plaintext == CONTENTS

expect_failure(lambda: validate(archive, password='0000-0000-0000-0000-0000'))

damaged_body = bytearray(archive)
damaged_body[len(prefix) + 5] ^= 1
expect_failure(lambda: validate(damaged_body))

damaged_magic = bytearray(archive)
damaged_magic[0] ^= 1
expect_failure(lambda: validate(damaged_magic))

aes_marker = b'\x24\x06\xf1\x07\x01'
marker_offset = archive.find(aes_marker)
assert marker_offset > len(prefix) + len(builder.body)
damaged_metadata = bytearray(archive)
damaged_metadata[marker_offset] ^= 1
expect_failure(lambda: validate(damaged_metadata))

for truncate_at in (
        0,
        11,
        len(prefix) - 1,
        len(prefix) + len(builder.body) - 1,
        len(archive) - 1):
    expect_failure(lambda: validate(archive[:truncate_at]))

expect_failure(lambda: validate(archive, max_size=len(CONTENTS) - 1))

if 'return_value' in globals():
    return_value.write(b'OK')
