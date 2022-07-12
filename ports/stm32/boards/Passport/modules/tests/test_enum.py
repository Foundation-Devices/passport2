# SPDX-FileCopyrightText: 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Test that the Enum utility module works.

import sys
import os

sys.path.insert(1, os.path.join(sys.path[0], '..'))


def test_enum():
    from Enum import enum

    EXAMPLE_ENUM = enum('VARIANT1', 'VARIANT2', 'VARIANT3')

    assert EXAMPLE_ENUM.VARIANT1 is not None
    assert EXAMPLE_ENUM.VARIANT2 is not None
    assert EXAMPLE_ENUM.VARIANT3 is not None
