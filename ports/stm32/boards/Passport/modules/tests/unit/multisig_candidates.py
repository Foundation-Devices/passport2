# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# A multisig wallet only matches a saved one with the same cosigner set:
# sharing some cosigners with a larger wallet makes it a different wallet.

import common

from multisig_wallet import MultisigWallet
from public_constants import AF_P2WSH

DERIVATION = "m/48'/0'/0'/2'"
A, B, C = 0x11111111, 0x22222222, 0x33333333


def wallet(name, m, xfps):
    keys = [(xfp, DERIVATION, 'xpub-{:08x}'.format(xfp)) for xfp in xfps]
    return MultisigWallet(name, (m, len(xfps)), keys, 1, addr_fmt=AF_P2WSH, deriv=DERIVATION)


class MockSettings:
    def __init__(self, wallets):
        self.records = [w.serialize() for w in wallets]

    def get(self, key, default=None):
        return self.records if key == 'multisig' else default


original_settings = common.settings
try:
    common.settings = MockSettings([wallet('Vault', 2, [A, B, C])])

    # A 2-of-2 over two of the vault's cosigners is a new wallet, not a
    # duplicate of the vault.
    assert wallet('Pair', 2, [A, B]).has_similar() == (None, [], 0)

    # The same cosigner set is still recognized, as before.
    assert wallet('Vault', 2, [A, B, C]).has_similar() == (None, [], 1)
    _, diffs, count = wallet('Vault', 3, [A, B, C]).has_similar()
    assert 'M differs' in diffs and count == 1

    # Signing picks the wallet whose cosigner set the PSBT names, not a
    # larger wallet that merely contains those cosigners.
    common.settings = MockSettings([wallet('Vault', 2, [A, B, C]), wallet('Pair', 2, [A, B])])
    pair_paths = wallet('Pair', 2, [A, B]).get_xfp_paths()
    assert [w.name for w in MultisigWallet.find_candidates(pair_paths)] == ['Pair']
    vault_paths = wallet('Vault', 2, [A, B, C]).get_xfp_paths()
    assert [w.name for w in MultisigWallet.find_candidates(vault_paths)] == ['Vault']
finally:
    common.settings = original_settings

return_value.write(b'OK')
