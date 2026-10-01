# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Exercise PSBT review methods on the host without loading device bindings."""

import ast
import asyncio
import gc
import io
import sys
import types
from pathlib import Path

import pytest


MODULES = Path(__file__).resolve().parents[1]


def load_method(path, class_name, method_name):
    tree = ast.parse((MODULES / path).read_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    method = next(node for node in cls.body if getattr(node, 'name', None) == method_name)
    namespace = {'gc': gc, 'HIGHLIGHT_TEXT_HEX': 0, 'BLACK_HEX': 0,
                 'recolor': lambda color, text: text}
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), namespace)
    return namespace[method_name]


consider_outputs = load_method('psbt.py', 'psbtObject', 'consider_outputs')
render_warnings = load_method('flows/sign_psbt_common_flow.py', 'SignPsbtCommonFlow', 'render_warnings')
show_warnings = load_method('flows/sign_psbt_common_flow.py', 'SignPsbtCommonFlow', 'show_warnings')


@pytest.mark.parametrize('policy', [None, (1, 1), (1, 2), (1, 15), (2, 3), (3, 3)])
@pytest.mark.parametrize('change', [0, 500, 1000])
def test_one_of_n_warning_preserves_existing_wallets(monkeypatch, policy, change):
    validations = []
    outputs = [types.SimpleNamespace(is_change=False), types.SimpleNamespace(is_change=True)]
    for output in outputs:
        output.validate = lambda *args: validations.append(args)
    wallet = types.SimpleNamespace(M=policy[0], N=policy[1]) if policy else None
    psbt = types.SimpleNamespace(
        active_multisig=wallet, my_xfp=123, outputs=outputs, warnings=[], self_send=False,
        total_value_out=1000, fee_is_verified=True,
        output_iter=lambda: iter(enumerate([types.SimpleNamespace(nValue=1000 - change),
                                           types.SimpleNamespace(nValue=change)])),
        calculate_fee=lambda: 1, consider_dangerous_change=lambda xfp: None)
    consider_outputs(psbt)
    assert len(validations) == 2
    assert psbt.self_send == (change == 1000)
    expected_warning = policy is not None and policy[0] == 1 and policy[1] > 1
    assert bool(psbt.warnings) == expected_warning
    assert len(psbt.warnings) == int(expected_warning)
    if expected_warning:
        monkeypatch.setitem(sys.modules, 'uio', io)
        flow = types.SimpleNamespace(psbt=psbt, chain=types.SimpleNamespace(render_value=lambda v: (v, 'sats')))
        text = render_warnings(flow)
        assert '1-of-{} Multisig'.format(policy[1]) in text
        assert 'Any other cosigner can spend' in text
        assert 'including change' in text
        assert 'without approval from this wallet' in text


@pytest.mark.parametrize('approve', [False, True])
def test_warning_must_be_acknowledged_before_signing(monkeypatch, approve):
    events = []

    class MockPage:
        def __init__(self, text, **kwargs):
            assert text == '1-of-2 Multisig warning'

        async def show(self):
            events.append('review')
            return approve

    monkeypatch.setitem(sys.modules, 'pages', types.SimpleNamespace(LongTextPage=MockPage))
    signing_state = object()
    flow = types.SimpleNamespace(
        render_warnings=lambda: '1-of-2 Multisig warning', header='Transaction Info',
        back=lambda: events.append('back'), goto=lambda state: events.append(state),
        sign_transaction=signing_state)
    asyncio.run(show_warnings(flow))
    assert events == ['review', signing_state if approve else 'back']
