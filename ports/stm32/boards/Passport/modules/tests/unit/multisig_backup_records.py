# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Multisig records restored from a backup are kept only when this firmware can
# use them.

import chains
import trezorcrypto

from multisig_wallet import MultisigWallet, validate_backup_multisig_records
from public_constants import AF_P2SH, AF_P2WSH

DERIVATION = "m/48'/0'/0'/2'"
PATH = [0x80000000 | 48, 0x80000000, 0x80000000, 0x80000000 | 2]
TESTNET_DERIVATION = "m/48'/1'/0'/2'"
TESTNET_PATH = [0x80000000 | 48, 0x80000000 | 1, 0x80000000, 0x80000000 | 2]


def root_from(seed_byte):
    seed = trezorcrypto.bip39.seed(trezorcrypto.bip39.from_data(bytes([seed_byte]) * 16), '')
    return trezorcrypto.bip32.from_seed(seed, 'secp256k1')


def derive(root, path):
    child = root.clone()
    for element in path:
        child.derive(element)
    return child


def key_entry(root, chain_name='BTC', derivation=DERIVATION, path=PATH):
    xpub = chains.get_chain(chain_name).serialize_public(derive(root, path), AF_P2SH)
    return (root.my_fingerprint(), derivation, xpub)


def record(keys, m=2, addr_fmt=AF_P2WSH, chain_type='BTC', name='Vault'):
    return MultisigWallet(name, (m, len(keys)), keys, 1, addr_fmt=addr_fmt,
                          chain_type=chain_type, deriv=keys[0][1]).serialize()


ROOT = root_from(1)
COSIGNER_A = root_from(2)
COSIGNER_B = root_from(3)
ROOT_XFP = ROOT.my_fingerprint()


def derive_root_node(path):
    return derive(ROOT, path)


def kept(records):
    return validate_backup_multisig_records(records, ROOT_XFP, derive_root_node)


mine = key_entry(ROOT)
cosigner_a = key_entry(COSIGNER_A)
cosigner_b = key_entry(COSIGNER_B)

# A record Passport itself would have created is kept unchanged.
valid = record([mine, cosigner_a, cosigner_b])
assert kept([valid]) == [valid]

# So is one where no key claims the backup's root, as with a config created
# while a passphrase was active: those keys cannot be checked here.
passphrase_wallet = record([cosigner_a, cosigner_b])
assert kept([passphrase_wallet]) == [passphrase_wallet]

# Testnet records are checked against the testnet chain.
testnet = record([key_entry(ROOT, 'TBTC', TESTNET_DERIVATION, TESTNET_PATH),
                  key_entry(COSIGNER_A, 'TBTC', TESTNET_DERIVATION, TESTNET_PATH)],
                 chain_type='TBTC')
assert kept([testnet]) == [testnet]

# A key that claims the backup's root fingerprint must derive from that root.
impostor = (ROOT_XFP, DERIVATION, cosigner_a[2])
assert kept([record([impostor, cosigner_b])]) == []

# Each xpub must belong to the record's chain.
assert kept([record([mine, cosigner_a], chain_type='TBTC')]) == []

# The derivation path depth must match the xpub's depth.
shallow = (cosigner_a[0], "m/48'/0'/0'", cosigner_a[2])
assert kept([record([mine, shallow])]) == []

# M-of-N and key counts must be in range, and the format must be a script.
assert kept([record([mine, cosigner_a], m=3)]) == []
assert kept([record([mine, cosigner_a], addr_fmt=0)]) == []
wrong_count = list(valid)
wrong_count[1] = (2, 4)
assert kept([wrong_count]) == []

# Every xpub must parse.
assert kept([record([mine, (cosigner_a[0], DERIVATION, 'xpub' + 'A' * 107)])]) == []

# Records that do not even deserialize, and a non-list, are dropped.
assert kept(['garbage', None, ('name', (2, 2))]) == []
assert kept('not a list') == []

# Invalid records are dropped individually; valid ones around them are kept.
assert kept([valid, 'garbage', passphrase_wallet]) == [valid, passphrase_wallet]

return_value.write(b'OK')
