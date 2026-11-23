# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Host tests for clearing the internal settings flash on color devices."""

import asyncio
import runpy
import sys
import types
from pathlib import Path

import pytest


MODULES = Path(__file__).resolve().parents[2]
FLASH_START = 0x81E0000
FLASH_LENGTH = 0x20000
ERASED = 0xFF


@pytest.fixture
def device(monkeypatch):
    state = types.SimpleNamespace(flash=bytearray([ERASED]) * FLASH_LENGTH, erases=0, reads=0)

    def bytearray_at(addr, length):
        state.reads += 1
        offset = addr - FLASH_START
        assert 0 <= offset and offset + length <= FLASH_LENGTH
        return state.flash[offset:offset + length]

    class SettingsFlash:
        def erase(self):
            state.erases += 1
            state.flash[:] = bytearray([ERASED]) * FLASH_LENGTH

    class Settings:
        def __init__(self, loop):
            pass

        def get(self, key, default=None):
            return default

    passport = types.ModuleType('passport')
    passport.IS_COLOR = True
    passport.IS_SIMULATOR = False
    passport.SettingsFlash = SettingsFlash
    uctypes = types.ModuleType('uctypes')
    uctypes.bytearray_at = bytearray_at
    settings = types.ModuleType('settings')
    settings.SETTINGS_FLASH_START = FLASH_START
    settings.SETTINGS_FLASH_LENGTH = FLASH_LENGTH
    settings.Settings = Settings
    ext_settings = types.ModuleType('ext_settings')
    ext_settings.ExtSettings = object
    version = types.ModuleType('version')
    version.Version = object
    for name, module in (('passport', passport), ('uctypes', uctypes), ('settings', settings),
                         ('ext_settings', ext_settings), ('version', version),
                         ('common', types.ModuleType('common')),
                         ('trezorcrypto', types.ModuleType('trezorcrypto'))):
        monkeypatch.setitem(sys.modules, name, module)

    module = runpy.run_path(str(MODULES / 'schema_evolution.py'))
    state.passport = passport
    state.boot = lambda: asyncio.run(module['handle_foundational_evolutions']())
    return state


@pytest.mark.parametrize('offset', [0, 31, FLASH_LENGTH // 2, FLASH_LENGTH - 1])
def test_color_device_erases_anything_left(device, offset):
    device.flash[offset] = 0
    device.boot()
    assert device.erases == 1
    assert all(byte == ERASED for byte in device.flash)

    # Once it holds nothing, later boots only check it.
    device.boot()
    assert device.erases == 1


def test_color_device_leaves_erased_flash_alone(device):
    device.boot()
    assert device.erases == 0
    assert device.reads > 0


@pytest.mark.parametrize('failure', ['unavailable', 'erase'])
def test_color_device_still_boots_when_the_erase_fails(device, failure):
    device.flash[0] = 0
    if failure == 'unavailable':
        del device.passport.SettingsFlash
    else:
        def erase(self):
            raise OSError('flash error')
        device.passport.SettingsFlash.erase = erase

    device.boot()
    assert device.flash[0] == 0


def test_mono_device_keeps_its_settings(device):
    device.passport.IS_COLOR = False
    device.flash[0] = 0
    device.boot()
    assert device.erases == 0
    assert device.flash[0] == 0


def test_simulator_does_not_touch_memory(device):
    device.passport.IS_SIMULATOR = True
    device.flash[0] = 0
    device.boot()
    assert device.erases == 0
    assert device.reads == 0
