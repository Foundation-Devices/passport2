# SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundation.xyz>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Test that the version module works.

import sys
import os

sys.path.insert(1, os.path.join(sys.path[0], '..'))


def test_version_operators():
    from version import Version

    assert Version('1.0.0') == Version('1.0.0')
    assert Version('1.0.1') > Version('1.0.0')
    assert Version('1.1.0') > Version('1.0.1')
    assert Version('1.0.0') < Version('1.0.1')
    assert Version('1.0.1') < Version('1.1.0')

    assert Version('1.2.3') < Version('1.2.4')
    assert Version('1.2.13') > Version('1.2.4')
    assert Version('1.3.13') > Version('1.2.4')
    assert Version('2.2.4') < Version('2.3.13')
