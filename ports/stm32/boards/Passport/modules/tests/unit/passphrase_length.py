# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# MAX_PASSPHRASE_LENGTH is what the passphrase entry page is capped at, and it has
# to match what mnemonic_to_seed() actually feeds to the KDF. A passphrase longer
# than that derives a wallet no other BIP39 wallet would reproduce, so the two
# numbers are pinned to each other here rather than left to drift.

import trezorcrypto

from constants import MAX_PASSPHRASE_LENGTH

MNEMONIC = trezorcrypto.bip39.from_data(bytes(16))


def seed_for(passphrase):
    return trezorcrypto.bip39.seed(MNEMONIC, passphrase)


at_cap = 'a' * MAX_PASSPHRASE_LENGTH
one_short = 'a' * (MAX_PASSPHRASE_LENGTH - 1)

# Every byte up to the cap reaches the KDF, so changing the last one changes the
# seed. If the cap were above what the KDF reads, this would not hold.
assert seed_for(at_cap) != seed_for(one_short + 'b')
assert seed_for(at_cap) != seed_for(one_short)

# One byte past the cap does not reach it, and nothing tells the user. That is the
# whole reason entry is capped where it is.
assert seed_for(at_cap) == seed_for(at_cap + 'b')
assert seed_for(at_cap) == seed_for(at_cap + 'bbbbbbbbbb')

# Ordinary passphrases are unaffected, including the empty one.
assert seed_for('') != seed_for('a')
assert seed_for('correct horse') != seed_for('correct horse ')

# Entry is ASCII only - lower, upper, digits, space and the symbol picker - so a
# character of input is always a byte of passphrase, and the cap can be counted in
# either. Guard that, since a cap in characters over a KDF that reads bytes would
# be the same defect again.
KEYBOARD = ('abcdefghijklmnopqrstuvwxyz'
            'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
            '0123456789 '
            '!@#$%^&*+/-=\\?|~_"`\',.:;()[]{}<>')

assert len(KEYBOARD.encode()) == len(KEYBOARD)

return_value.write(b'OK')
