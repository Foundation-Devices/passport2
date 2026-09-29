# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Test backup restore settings filtering.

from tasks.restore_backup_task import restore_settings_from_backup


class FakeSettings:
    def __init__(self):
        self.values = {}

    def set(self, key, value):
        self.values[key] = value


vals = {
    'chain': 'BTC',
    'xfp': 'top-level metadata is ignored here',
    'setting.xfp': 0x11111111,
    'setting.xpub': 'attacker-xpub',
    'setting.root_xfp': 0x22222222,
    'setting.bip39_passphrase': 'runtime-only',
    'setting.units': 'sats',
    'setting.backup_quiz': True,
}

settings = FakeSettings()
restore_settings_from_backup(vals, settings)

assert settings.values == {
    'units': 'sats',
    'backup_quiz': True,
}


# Restore the whole task and read back what was persisted, which the filtering
# test above cannot do: capture_xpub() shadows xfp/xpub with volatile values, so
# only clearing those and reading the persisted store shows whether save=True
# actually wrote the derived identity.

import chains
import common
import stash
import trezorcrypto
import uasyncio as asyncio

import tasks.restore_backup_task as restore_module
from tasks.restore_backup_task import restore_backup_task
from ubinascii import hexlify as b2a_hex


ATTACKER_XFP = 0x11111111
ATTACKER_XPUB = 'attacker-xpub'

seed_bits = bytes(range(16))
secret = stash.SecretStash.encode(seed_bits=seed_bits)

# Derive the expected identity here rather than reusing capture_xpub(), so the
# assertions below fail if the task persists anything other than the identity
# belonging to the restored secret.
expected_node = trezorcrypto.bip32.from_seed(
    trezorcrypto.bip39.seed(trezorcrypto.bip39.from_data(seed_bits), ''), 'secp256k1')
expected_xfp = expected_node.my_fingerprint()
expected_xpub = chains.get_chain('BTC').serialize_public(expected_node)

assert expected_xfp != ATTACKER_XFP

BACKUP_LINES = (
    '# Passport backup file',
    'raw_secret = "%s"' % b2a_hex(secret).decode(),
    'chain = "BTC"',
    'setting.xfp = 286331153',           # 0x11111111
    'setting.xpub = "attacker-xpub"',
    'setting.root_xfp = 572662306',      # 0x22222222
    'setting.bip39_passphrase = "runtime-only"',
    'setting.units = "sats"',
    'setting.backup_quiz = true',
)
BACKUP_CONTENTS = ('\n'.join(BACKUP_LINES) + '\n').encode()


class StoredSettings:
    # Models the split the real settings object has: set() persists, and
    # set_volatile() shadows it until the overrides are cleared.
    def __init__(self):
        self.persisted = {}
        self.volatile = {}
        self.saves = 0

    def get(self, key, default=None):
        if key in self.volatile:
            return self.volatile[key]
        return self.persisted.get(key, default)

    def set(self, key, value):
        self.persisted[key] = value

    def set_volatile(self, key, value):
        self.volatile[key] = value

    def save(self):
        self.saves += 1

    def clear_volatile(self):
        self.volatile.clear()


class FakePa:
    def __init__(self):
        self.calls = []

    def change(self, new_secret=None):
        self.calls.append('change')

    async def new_main_secret(self, raw, chain):
        self.calls.append('new_main_secret')


class FakeCardSlot:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class FakeFile:
    def close(self):
        pass


class FakeBuilder:
    def read_file(self, fd, password, maxsize, progress_fcn=None):
        return ('backup.txt', BACKUP_CONTENTS)


class FakeCompat7z:
    Builder = FakeBuilder

    @staticmethod
    def check_file_headers(fd):
        pass


async def run_restore():
    results = []

    async def on_done(error):
        results.append(error)

    await restore_backup_task(on_done, 'password', '/sd/backup.7z')
    return results


stored = StoredSettings()
pa = FakePa()

# Set the module-level open() before the try, so the finally can always undo it.
restore_module.open = lambda path, mode: FakeFile()
originals = (common.settings, common.pa, restore_module.compat7z, restore_module.CardSlot)
try:
    common.settings = stored
    common.pa = pa
    restore_module.compat7z = FakeCompat7z
    restore_module.CardSlot = FakeCardSlot

    assert asyncio.run(run_restore()) == [None]
finally:
    common.settings, common.pa, restore_module.compat7z, restore_module.CardSlot = originals
    del restore_module.open

assert pa.calls == ['change', 'new_main_secret']

# The volatile copies hide whether anything was persisted, so drop them first.
stored.clear_volatile()

# Identity comes from the restored secret, never from the backup.
assert stored.persisted['xfp'] == expected_xfp
assert stored.persisted['xpub'] == expected_xpub
assert stored.persisted['xfp'] != ATTACKER_XFP
assert stored.persisted['xpub'] != ATTACKER_XPUB
assert stored.saves >= 1

# Ordinary settings survive, the quiz is reset, and runtime-only values are dropped.
assert stored.persisted['units'] == 'sats'
assert stored.persisted['backup_quiz'] is False
assert 'root_xfp' not in stored.persisted
assert 'bip39_passphrase' not in stored.persisted

return_value.write(b'OK')
