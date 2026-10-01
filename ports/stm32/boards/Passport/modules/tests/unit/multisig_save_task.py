# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Rollback and error reporting when saving a multisig wallet fails.

import common
import uasyncio as asyncio

from errors import Error
from ext_settings import SettingsOutOfSpace
from tasks.save_multisig_wallet_task import save_multisig_wallet_task


EXISTING = [{'name': 'existing'}]


class MockSettings:
    # save() raises the next queued error, so a test can fail the first save
    # and still control what the rollback save does.
    def __init__(self, multisig, save_errors=()):
        self.values = {'multisig': multisig}
        self.save_errors = list(save_errors)
        self.saves = 0

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value):
        self.values[key] = value

    def save(self):
        self.saves += 1
        if self.save_errors:
            error = self.save_errors.pop(0)
            if error is not None:
                raise error


class MockWallet:
    def __init__(self, storage_idx=-1, name='wallet'):
        self.storage_idx = storage_idx
        self.name = name

    def serialize(self):
        return {'name': self.name}


async def save(settings, ms):
    # Collect every on_done call so a test can assert it happened exactly once.
    results = []

    async def on_done(error):
        results.append(error)

    common.settings = settings
    await save_multisig_wallet_task(on_done, ms)
    return results


async def run_tests():
    original_settings = common.settings
    try:
        # A successful save reports no error and leaves the appended wallet in place.
        settings = MockSettings([dict(entry) for entry in EXISTING])
        assert await save(settings, MockWallet()) == [None]
        assert settings.saves == 1
        assert settings.get('multisig') == EXISTING + [{'name': 'wallet'}]

        # Out of space rolls back and reports the specific error, once.
        settings = MockSettings([dict(entry) for entry in EXISTING],
                                [SettingsOutOfSpace('too big'), None])
        assert await save(settings, MockWallet()) == [Error.USER_SETTINGS_FULL]
        assert settings.get('multisig') == EXISTING
        assert settings.saves == 2

        # Any other save failure rolls back and reports the generic error, once.
        settings = MockSettings([dict(entry) for entry in EXISTING],
                                [ValueError('flash write failed'), None])
        assert await save(settings, MockWallet()) == [Error.USER_SETTINGS_SAVE_FAILED]
        assert settings.get('multisig') == EXISTING
        assert settings.saves == 2

        # A rollback that itself fails is swallowed, and the original error is
        # still reported exactly once.
        settings = MockSettings([dict(entry) for entry in EXISTING],
                                [SettingsOutOfSpace('too big'), RuntimeError('rollback failed')])
        assert await save(settings, MockWallet()) == [Error.USER_SETTINGS_FULL]
        assert settings.get('multisig') == EXISTING
        assert settings.saves == 2

        settings = MockSettings([dict(entry) for entry in EXISTING],
                                [ValueError('flash write failed'), RuntimeError('rollback failed')])
        assert await save(settings, MockWallet()) == [Error.USER_SETTINGS_SAVE_FAILED]
        assert settings.saves == 2

        # Replacing an existing wallet restores the entry it overwrote.
        stored = [{'name': 'a'}, {'name': 'b'}]
        settings = MockSettings([dict(entry) for entry in stored],
                                [SettingsOutOfSpace('too big'), None])
        wallet = MockWallet(storage_idx=1, name='replacement')
        assert await save(settings, wallet) == [Error.USER_SETTINGS_FULL]
        assert settings.get('multisig') == stored

        return_value.write(b'OK')
    finally:
        common.settings = original_settings


asyncio.run(run_tests())
