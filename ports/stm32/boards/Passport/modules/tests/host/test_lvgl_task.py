# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Host tests: an exception out of LVGL's timer handler restarts Passport."""

import runpy
import sys
import types
from pathlib import Path

import pytest


MODULES = Path(__file__).resolve().parents[2]


@pytest.fixture
def lvgl_task(monkeypatch):
    resets = []

    class System:
        def reset(self):
            resets.append(True)

    lvgl = types.ModuleType('lvgl')
    lvgl.timer_handler = lambda: None
    passport = types.ModuleType('passport')
    passport.IS_SIMULATOR = False
    passport.System = System
    stubs = {
        'lvgl': lvgl,
        'passport': passport,
        'uasyncio': types.SimpleNamespace(sleep_ms=None),
        'utime': types.SimpleNamespace(ticks_ms=None),
    }
    for name, stub in stubs.items():
        monkeypatch.setitem(sys.modules, name, stub)
    monkeypatch.setattr(sys, 'print_exception', lambda e: None, raising=False)

    run_timers = runpy.run_path(str(MODULES / 'tasks/lvgl_task.py'))['run_timers']
    return lvgl, run_timers, resets


def test_timers_run_without_a_restart(lvgl_task):
    lvgl, run_timers, resets = lvgl_task
    ran = []
    lvgl.timer_handler = lambda: ran.append(True)
    run_timers()
    assert ran == [True] and resets == []


@pytest.mark.parametrize('error', [MemoryError, ValueError])
def test_an_exception_out_of_the_timer_handler_restarts(lvgl_task, error):
    # The exception leaves LVGL marked as running its timers, so it would never draw
    # or read the keys again.
    lvgl, run_timers, resets = lvgl_task

    def timer_handler():
        raise error()

    lvgl.timer_handler = timer_handler
    run_timers()
    assert resets == [True]
