# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Host tests: a disabled Passport says so at login instead of asking for a PIN."""

import builtins
import runpy
import sys
import types
from pathlib import Path

import pytest


MODULES = Path(__file__).resolve().parents[2]


@pytest.fixture
def login_flow(monkeypatch):
    class Flow:
        def __init__(self, initial_state=None, name=None, statusbar=None):
            self.state = initial_state

    callgate = types.ModuleType('callgate')
    callgate.bricked = False
    callgate.get_is_bricked = lambda: callgate.bricked
    common = types.ModuleType('common')
    common.settings = types.SimpleNamespace(get=lambda key, default=None: default)
    common.pa = types.SimpleNamespace(attempts_left=0)

    stubs = {
        'lvgl': types.ModuleType('lvgl'),
        'flows': types.SimpleNamespace(Flow=Flow),
        'pages': types.SimpleNamespace(PINEntryPage=None, ShutdownPage=None, ErrorPage=None),
        'tasks': types.SimpleNamespace(login_task=None),
        'utils': types.SimpleNamespace(spinner_task=None),
        'serializations': types.SimpleNamespace(sha256=None),
        'microns': types.ModuleType('microns'),
        'common': common,
        'callgate': callgate,
    }
    for name, stub in stubs.items():
        monkeypatch.setitem(sys.modules, name, stub)
    monkeypatch.setattr(builtins, 'const', lambda value: value, raising=False)

    flow_class = runpy.run_path(str(MODULES / 'flows/login_flow.py'))['LoginFlow']

    def initial_state(attempts_left, bricked, pa_present=True):
        common.pa = types.SimpleNamespace(attempts_left=attempts_left) if pa_present else None
        callgate.bricked = bricked
        return flow_class().state.__name__

    return initial_state


def test_disabled_device_shows_the_disabled_message(login_flow):
    assert login_flow(attempts_left=0, bricked=True) == 'show_bricked_message'


@pytest.mark.parametrize('attempts_left,bricked,pa_present', [
    (21, False, True),   # normal login
    (3, False, True),    # a few attempts left
    (0, False, True),    # PIN setup failed at boot for another reason
    (5, True, True),     # attempts are known, so the PIN page handles it
    (0, True, False),    # no PIN state at all
])
def test_otherwise_the_pin_is_requested(login_flow, attempts_left, bricked, pa_present):
    assert login_flow(attempts_left, bricked, pa_present) == 'enter_pin'
