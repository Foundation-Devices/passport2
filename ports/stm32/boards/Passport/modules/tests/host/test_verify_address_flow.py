# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Host regressions for launching wallet-policy address verification."""

import builtins
import runpy
import sys
import types
from pathlib import Path


MODULES = Path(__file__).resolve().parents[2]


def test_policy_verification_does_not_require_an_active_account(monkeypatch):
    flows = types.ModuleType('flows')

    class Flow:
        def __init__(self, initial_state=None, name=None):
            self.state = initial_state
            self.name = name

    flows.Flow = Flow

    common = types.ModuleType('common')
    common.ui = types.SimpleNamespace(get_active_account=lambda: None)

    microns = types.ModuleType('microns')

    monkeypatch.setitem(sys.modules, 'flows', flows)
    monkeypatch.setitem(sys.modules, 'common', common)
    monkeypatch.setitem(sys.modules, 'microns', microns)
    monkeypatch.setattr(builtins, 'const', lambda value: value, raising=False)

    namespace = runpy.run_path(str(MODULES / 'flows/verify_address_flow.py'))
    verify_flow = namespace['VerifyAddressFlow'](
        sig_type='policy', wallet_policy=object())

    assert verify_flow.acct_num == 0
