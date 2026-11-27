# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# firmware_header.py - Check that a firmware update file still holds the checked header

from constants import FW_HEADER_SIZE


def header_unchanged(fp, expected, buf):
    """Compare the header at the start of `fp` with `expected`, the header checked when
    the file was picked. The file is read into `buf` a piece at a time, so no block the
    size of the header is needed from the heap. Leaves `fp` just past the header."""

    expected = memoryview(expected)
    buf = memoryview(buf)
    if len(expected) != FW_HEADER_SIZE:
        return False
    pos = 0
    while pos < FW_HEADER_SIZE:
        n = min(len(buf), FW_HEADER_SIZE - pos)
        if fp.readinto(buf[:n]) != n or buf[:n] != expected[pos:pos + n]:
            return False
        pos += n
    return True
