# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Host tests for Liana's file-based descriptor-key export."""

import runpy
import sys
import types
from pathlib import Path

import pytest
from embit.descriptor.arguments import Key


MODULES = Path(__file__).resolve().parents[2]


class _Node:
    pass


class _SensitiveValues:
    def __init__(self, expected_deriv, xpub):
        self.expected_deriv = expected_deriv
        self.xpub = xpub
        self.chain = types.SimpleNamespace(serialize_public=self.serialize_public)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def derive_path(self, deriv):
        assert deriv == self.expected_deriv
        return _Node()

    def serialize_public(self, node, addr_type):
        assert isinstance(node, _Node)
        assert addr_type == 1
        return self.xpub


@pytest.mark.parametrize(
    'coin_type,acct_num,expected_deriv,xpub', [
        (1, 0, "m/48'/1'/0'/2'",
         'tpubDEhFJsryccF9b2PaR3mgUBVfoYbpVaXsmpK6sonC8cysYcpJzYsZfiwkR9Ja'
         'oiNWCT9o1HN2bFccb2wMnAXGdKpW6nYQukZMZXfF32RnS6y'),
        (0, 7, "m/48'/0'/7'/2'",
         'xpub6Eak7S2MQqvUkxQ7MCf6hFRYyQ8tK9iaUsRm1nkNshKWvbhCysH83byA6akg'
         'm2ZjCvCLjco2XcwYDqNpBYdV5StSWMAEe12FaVsT8bTJBJC'),
    ])
def test_liana_export_is_a_raw_descriptor_key(
        monkeypatch, coin_type, acct_num, expected_deriv, xpub):
    chains = types.ModuleType('chains')
    chains.current_chain = lambda: types.SimpleNamespace(
        b44_cointype=coin_type)

    stash = types.ModuleType('stash')
    stash.SensitiveValues = lambda: _SensitiveValues(expected_deriv, xpub)

    common = types.ModuleType('common')
    common.settings = types.SimpleNamespace(get=lambda key: 0xA1B2C3D4)

    public_constants = types.ModuleType('public_constants')
    public_constants.AF_CLASSIC = 1
    public_constants.AF_P2WSH = 2

    utils = types.ModuleType('utils')
    utils.xfp2str = lambda value: 'A1B2C3D4'

    monkeypatch.setitem(sys.modules, 'chains', chains)
    monkeypatch.setitem(sys.modules, 'stash', stash)
    monkeypatch.setitem(sys.modules, 'common', common)
    monkeypatch.setitem(sys.modules, 'public_constants', public_constants)
    monkeypatch.setitem(sys.modules, 'utils', utils)

    namespace = runpy.run_path(str(MODULES / 'wallets/liana.py'))
    export, account_info = namespace['create_liana_export'](
        acct_num=acct_num)

    expected_origin = expected_deriv[2:]
    assert export == '[a1b2c3d4/{}]{}\n'.format(expected_origin, xpub)
    # Liana parses this file as a raw descriptor public key before trying its
    # Coldcard-specific JSON formats.
    assert Key.from_string(export.strip()) is not None
    assert account_info == [{
        'fmt': 2,
        'deriv': expected_deriv,
        'acct': acct_num,
        'xfp': 'a1b2c3d4',
    }]
