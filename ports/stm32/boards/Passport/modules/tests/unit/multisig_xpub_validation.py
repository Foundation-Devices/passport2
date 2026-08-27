# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

import multisig_wallet
import stash

from multisig_wallet import MultisigWallet
from public_constants import AF_P2SH


MY_XFP = 0x12345678
DERIVATION = "m/48'/0'/0'/2'"
PUBLIC_KEY = b'\x02' + (b'\x11' * 32)
CHAIN_CODE = b'\x22' * 32


class FakeNode:
    def __init__(self, public_key, chain_code):
        self._public_key = public_key
        self._chain_code = chain_code

    def depth(self):
        return 4

    def public_key(self):
        return self._public_key

    def chain_code(self):
        return self._chain_code


class FakeChain:
    ctype = 'BTC'

    @staticmethod
    def serialize_public(_node, addr_fmt):
        assert addr_fmt == AF_P2SH
        return 'normalized-xpub'


class FakeSensitiveValues:
    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc, _traceback):
        pass

    @staticmethod
    def derive_path(derivation):
        assert derivation == DERIVATION
        return FakeNode(PUBLIC_KEY, CHAIN_CODE)


def check_node(node):
    original_import_xpub = multisig_wallet.import_xpub
    original_sensitive_values = stash.SensitiveValues

    try:
        multisig_wallet.import_xpub = lambda _xpub: (node, FakeChain, AF_P2SH)
        stash.SensitiveValues = FakeSensitiveValues
        xpubs = []
        is_mine = MultisigWallet.check_xpub(
            MY_XFP,
            'imported-xpub',
            DERIVATION,
            'BTC',
            MY_XFP,
            xpubs,
        )
        return is_mine, xpubs
    finally:
        multisig_wallet.import_xpub = original_import_xpub
        stash.SensitiveValues = original_sensitive_values


is_mine, xpubs = check_node(FakeNode(PUBLIC_KEY, CHAIN_CODE))
assert is_mine
assert xpubs == [(MY_XFP, DERIVATION, 'normalized-xpub')]

try:
    check_node(FakeNode(PUBLIC_KEY, b'\x33' * 32))
except AssertionError as exc:
    assert 'wrong xpub' in str(exc)
else:
    raise AssertionError('Expected a substituted chain code to be rejected')

return_value.write(b'OK')
