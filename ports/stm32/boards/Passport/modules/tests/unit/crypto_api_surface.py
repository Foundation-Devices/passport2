# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# py.mk sets -DUSE_BIP39_GENERATE=0, so bip39.generate() is not part of the API
# surface. Passport generates seeds in new_seed_task rather than through it.

import trezorcrypto

assert not hasattr(trezorcrypto.bip39, 'generate'), \
    'bip39.generate() is exposed again, and USE_BIP39_GENERATE asks for it to be off'

# Everything else the seed flows use is still there.
for name in ('from_data', 'seed', 'check', 'find_word', 'complete_word',
             'word_completion_mask', 'get_word'):
    assert hasattr(trezorcrypto.bip39, name), 'bip39.{} went missing'.format(name)

# from_data() takes bytes the caller chose, so it stays: new_seed_task hands it the
# result of its own noise request. A known vector, to show it still works.
assert trezorcrypto.bip39.from_data(bytes(16)) == \
    'abandon abandon abandon abandon abandon abandon abandon abandon ' \
    'abandon abandon abandon about'
assert trezorcrypto.bip39.check(trezorcrypto.bip39.from_data(bytes(32)))

# ext_settings.py relies on both of these for wear levelling and padding.
assert len(trezorcrypto.random.bytes(256)) == 256

options = list(range(16))
trezorcrypto.random.shuffle(options)
assert sorted(options) == list(range(16))

return_value.write(b'OK')
