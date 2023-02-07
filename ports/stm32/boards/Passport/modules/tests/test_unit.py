# SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Run unit tests in the Unix MP build.

import pytest
from fixtures.simulator import *


@pytest.fixture
def test(exec_file):
    def doit(file):
        return exec_file('unit/' + file)

    return doit


def test_ext_settings(test):
    assert test('ext_settings.py') == b'OK'


def test_ui(test):
    assert test('ui.py') == b'OK'


def test_foundation(test):
    assert test('foundation.py') == b'OK'
