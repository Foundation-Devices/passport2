# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Host regressions for launching wallet-policy address verification."""

import asyncio
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


def test_successful_post_import_verification_exits_to_policy_menu(monkeypatch):
    flows = types.ModuleType('flows')

    class Flow:
        pass

    class VerifyAddressFlow:
        result = True

        def __init__(self, sig_type=None, wallet_policy=None):
            assert sig_type == 'policy'
            assert wallet_policy is not None

        async def run(self):
            return self.result

    flows.Flow = Flow
    flows.SaveToMicroSDFlow = type('SaveToMicroSDFlow', (), {})
    flows.VerifyAddressFlow = VerifyAddressFlow
    monkeypatch.setitem(sys.modules, 'flows', flows)

    namespace = runpy.run_path(str(MODULES / 'flows/wallet_policy_flow.py'))
    flow_class = namespace['ImportWalletPolicyFlow']

    flow = object.__new__(flow_class)
    flow.policy = object()
    results = []
    destinations = []
    flow.set_result = results.append
    flow.goto = lambda state, save_curr=True: destinations.append(
        (state, save_curr))

    asyncio.run(flow.verify_first_address())
    assert results == [True]
    assert destinations == []

    VerifyAddressFlow.result = False
    results.clear()
    asyncio.run(flow.verify_first_address())
    assert results == []
    assert destinations == [(flow.choose_next_action, False)]
