# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Host tests for which keys a Casa or Theya health check may sign with."""

import runpy
import sys
import types
from pathlib import Path

import pytest


MODULES = Path(__file__).resolve().parents[2]


@pytest.fixture
def is_health_check_path(monkeypatch):
    flows = types.ModuleType('flows')
    flows.Flow = object
    wallets = types.ModuleType('wallets')
    wallets_utils = types.ModuleType('wallets.utils')
    wallets_utils.get_addr_type_from_deriv = None
    wallets_utils.get_addr_type_from_string = None
    public_constants = types.ModuleType('public_constants')
    public_constants.AF_CLASSIC = 1
    public_constants.AF_P2TR = 2
    for name, module in (('flows', flows), ('wallets', wallets), ('wallets.utils', wallets_utils),
                         ('public_constants', public_constants)):
        monkeypatch.setitem(sys.modules, name, module)
    return runpy.run_path(str(MODULES / 'flows/health_check_common_flow.py'))['is_health_check_path']


# Paths as cleanup_deriv_path() returns them. The first entries in each list
# are the ones the services' own health checks use.
CASA_PATHS = ['m/49/0/1/0/0', 'm', '', "m/45'/0/0", "m/45'/1/3/1/7", 'm/49/1/0/0']
THEYA_PATHS = ["m/48'/0'/0'/2'/0/0", "m/48'/0'/0'/2'", "m/48'/1'/5'/1'/1/9"]
NEITHER = [
    "m/84'/0'/0'/0/0", "m/86'/0'/0'/0/0", "m/44'/0'/0'/0/0", "m/49'/0'/0'/0/0", "m/0",
    'm/49/0', 'm/49/2/1/0/0', 'm/49/0/1/2/0', "m/49/0/1/0/0'", 'm/49/0/1/0/0/0', "m/45/0/0",
    "m/48'/0'/0'/3'/0/0", "m/48'/0/0'/2'/0/0", "m/48'/0'/0/2'/0/0", "m/48'/2'/0'/2'",
    "m/48'/0'/0'/2'/2/0", "m/48'/0'/0'/2'/0/0/0", "m/48'/0'/0'",
]


@pytest.mark.parametrize('path', CASA_PATHS)
def test_casa_paths(is_health_check_path, path):
    assert is_health_check_path('Casa', path)
    assert not is_health_check_path('Theya', path)


@pytest.mark.parametrize('path', THEYA_PATHS)
def test_theya_paths(is_health_check_path, path):
    assert is_health_check_path('Theya', path)
    assert not is_health_check_path('Casa', path)


@pytest.mark.parametrize('path', NEITHER + CASA_PATHS + THEYA_PATHS)
def test_other_keys_and_services_are_refused(is_health_check_path, path):
    if path not in CASA_PATHS:
        assert not is_health_check_path('Casa', path)
    if path not in THEYA_PATHS:
        assert not is_health_check_path('Theya', path)
    assert not is_health_check_path(None, path)
    assert not is_health_check_path('Postmix', path)
