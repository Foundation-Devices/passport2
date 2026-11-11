# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Test backup restore settings filtering.

from constants import BACKUP_FILE_HEADER
from errors import Error
from tasks.restore_backup_task import restore_settings_from_backup

# Every backup Passport has written starts with this line, and restore relies
# on it, so it must never change.
assert BACKUP_FILE_HEADER == '# Passport backup file! DO NOT CHANGE.\n'


class MockSettings:
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

settings = MockSettings()
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
import ujson

import tasks.restore_backup_task as restore_module
from multisig_wallet import MultisigWallet
from public_constants import AF_P2SH, AF_P2WSH
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

# One multisig record that belongs to the restored seed, and one whose key
# claims the restored seed's fingerprint but is another seed's xpub.
MULTISIG_DERIVATION = "m/48'/0'/0'/2'"
MULTISIG_PATH = [0x80000000 | 48, 0x80000000, 0x80000000, 0x80000000 | 2]


def multisig_xpub(root):
    node = root.clone()
    for element in MULTISIG_PATH:
        node.derive(element)
    return chains.get_chain('BTC').serialize_public(node, AF_P2SH)


cosigner_root = trezorcrypto.bip32.from_seed(
    trezorcrypto.bip39.seed(trezorcrypto.bip39.from_data(bytes(range(16, 32))), ''), 'secp256k1')
own_key = (expected_xfp, MULTISIG_DERIVATION, multisig_xpub(expected_node))
cosigner_key = (cosigner_root.my_fingerprint(), MULTISIG_DERIVATION, multisig_xpub(cosigner_root))
impostor_key = (expected_xfp, MULTISIG_DERIVATION, multisig_xpub(cosigner_root))
# The JSON round trip turns tuples into the lists a restored record contains.
valid_multisig = ujson.loads(ujson.dumps(MultisigWallet(
    'Vault', (1, 2), [own_key, cosigner_key], 1, addr_fmt=AF_P2WSH, deriv=MULTISIG_DERIVATION).serialize()))
impostor_multisig = MultisigWallet(
    'Swap', (1, 2), [impostor_key, (0x33333333, MULTISIG_DERIVATION, cosigner_key[2])], 2,
    addr_fmt=AF_P2WSH, deriv=MULTISIG_DERIVATION).serialize()
second_multisig = ujson.loads(ujson.dumps(MultisigWallet(
    'Joint', (2, 2), [own_key, cosigner_key], 3, addr_fmt=AF_P2WSH, deriv=MULTISIG_DERIVATION).serialize()))

# Records that deserialize but hold a field of the wrong type, so a check
# raises partway through instead of returning False.
string_m = ujson.loads(ujson.dumps(valid_multisig))
string_m[1] = ['1', 2]
string_format = ujson.loads(ujson.dumps(valid_multisig))
string_format[3]['ft'] = 'p2wsh'

BACKUP_LINES = (
    '# Passport backup file! DO NOT CHANGE.',
    'raw_secret = "%s"' % b2a_hex(secret).decode(),
    'chain = "BTC"',
    'setting.xfp = 286331153',           # 0x11111111
    'setting.xpub = "attacker-xpub"',
    'setting.root_xfp = 572662306',      # 0x22222222
    'setting.bip39_passphrase = "runtime-only"',
    'setting.units = "sats"',
    'setting.backup_quiz = true',
    'setting.multisig = %s' % ujson.dumps(
        [valid_multisig, string_m, impostor_multisig, string_format, second_multisig]),
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


class MockPa:
    def __init__(self):
        self.calls = []

    def change(self, new_secret=None):
        self.calls.append('change')

    async def new_main_secret(self, raw, chain):
        self.calls.append('new_main_secret')


class MockCardSlot:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class MockFile:
    def close(self):
        pass


class MockBuilder:
    contents = BACKUP_CONTENTS

    def read_file(self, fd, password, maxsize, progress_fcn=None):
        return ('backup.txt', self.contents)


class MockCompat7z:
    Builder = MockBuilder

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
pa = MockPa()

# Set the module-level open() before the try, so the finally can always undo it.
restore_module.open = lambda path, mode: MockFile()
originals = (common.settings, common.pa, restore_module.compat7z, restore_module.CardSlot)
try:
    common.settings = stored
    common.pa = pa
    restore_module.compat7z = MockCompat7z
    restore_module.CardSlot = MockCardSlot

    # A backup whose first line isn't the exact header is refused before the
    # secret or any setting is touched, even though the rest is intact.
    for first_bytes in (b'# Passport backup file\n', b'#\nsetting.a = 1\n'):
        MockBuilder.contents = first_bytes + BACKUP_CONTENTS[len(first_bytes):]
        assert MockBuilder.contents[0:1] == b'#' and MockBuilder.contents != BACKUP_CONTENTS
        assert asyncio.run(run_restore()) == [Error.CORRUPT_BACKUP_FILE]
        assert pa.calls == []
        assert stored.persisted == {} and stored.volatile == {} and stored.saves == 0

    MockBuilder.contents = BACKUP_CONTENTS
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

# The multisig records that belong to the restored seed are restored. The one
# whose key does not derive from it and the two with mistyped fields are
# dropped, and the seed is still restored.
assert stored.persisted['multisig'] == [valid_multisig, second_multisig]

return_value.write(b'OK')
