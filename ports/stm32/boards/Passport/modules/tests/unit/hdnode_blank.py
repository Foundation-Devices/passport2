# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# HDNode.blank() wipes key material on demand rather than waiting for the node to be
# collected. It clears the whole node, curve pointer included, so a blanked node can
# only be dropped; every caller does that immediately.

import trezorcrypto

from stash import blank_object

SEED = bytes(range(64))
XPUB_VERSION = 0x0488b21e
ZEROS = bytes(32)


def fresh_node():
    node = trezorcrypto.bip32.from_seed(SEED, 'secp256k1')
    node.derive(0x80000000)
    return node


def assert_blanked(node):
    assert node.private_key() == ZEROS
    assert node.private_key_ext() == ZEROS
    assert node.chain_code() == ZEROS
    assert node.depth() == 0
    assert node.child_num() == 0
    assert node.fingerprint() == 0


node = fresh_node()

# Everything that blank() clears is set to begin with, so the checks below mean
# something.
assert node.private_key() != ZEROS
assert node.chain_code() != ZEROS
assert node.depth() == 1
assert node.child_num() == 0x80000000
assert node.fingerprint() != 0

node.blank()
assert_blanked(node)

# Blanking an already blank node is not an error.
node.blank()
assert_blanked(node)

# stash.blank_object() reaches the same wipe. Until now its HDNode branch was a
# no-op, so SensitiveValues.__exit__ left every registered node in the heap.
node = fresh_node()
assert node.private_key() != ZEROS
blank_object(node)
assert_blanked(node)

# A node that carries no private key still has a chain code worth wiping.
public_node = trezorcrypto.bip32.deserialize(fresh_node().serialize_public(XPUB_VERSION),
                                             XPUB_VERSION, True)
assert public_node.chain_code() != ZEROS
public_node.blank()
assert_blanked(public_node)

# Anything blank_object() cannot wipe is still refused rather than passed over.
try:
    blank_object(1)
    raise RuntimeError('expected TypeError')
except TypeError:
    pass

return_value.write(b'OK')
