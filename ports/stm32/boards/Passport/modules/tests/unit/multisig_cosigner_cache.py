# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# MultisigWallet keeps cosigner nodes to derive each input's key quickly, but a PSBT
# spread over many branches can't grow that cache without limit, and every key it
# derives is still the right one.

from multisig_wallet import MultisigWallet

H = 0x80000000
ACCOUNT = [48 | H, 0 | H, 0 | H, 2 | H]


class Node:
    def __init__(self, path=()):
        self.path = list(path)

    def depth(self):
        return len(ACCOUNT)

    def clone(self):
        return Node(self.path)

    def derive(self, index, public):
        assert public
        self.path.append(index)


class Chain:
    def __init__(self):
        self.decoded = 0

    def deserialize_node(self, xpub, af):
        self.decoded += 1
        return Node()


class Wallet:
    pass


wallet = Wallet()
wallet.xpubs = [(0, 'm', 'xpub%d' % idx) for idx in range(15)]
chain = Chain()

for branch in range(40):
    for xp_idx in range(15):
        node, depth = MultisigWallet._cosigner_node(wallet, chain, xp_idx, ACCOUNT + [branch, 7])
        assert depth == len(ACCOUNT)
        assert node.path == [branch, 7], node.path

assert len(wallet._cosigner_nodes) <= 48, len(wallet._cosigner_nodes)

# The first branch's nodes were kept, so its inputs don't decode any xpub again.
decoded = chain.decoded
for xp_idx in range(15):
    MultisigWallet._cosigner_node(wallet, chain, xp_idx, ACCOUNT + [0, 8])
assert chain.decoded == decoded

return_value.write(b'OK')
