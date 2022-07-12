# SPDX-FileCopyrightText: 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Pytest configuration.


def pytest_addoption(parser):
    parser.addoption("--simulatordir", action="store", default="Simulator root directory")


def pytest_generate_tests(metafunc):
    # This is called for every test. Only get/set command line arguments
    # if the argument is specified in the list of test "fixturenames".
    option_value = metafunc.config.option.simulatordir
    if 'simulatordir' in metafunc.fixturenames and option_value is not None:
        metafunc.parametrize("simulatordir", [option_value])
