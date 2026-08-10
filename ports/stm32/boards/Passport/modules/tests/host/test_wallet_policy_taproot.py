# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

import builtins
import hashlib
import os
import sys
import types

import pytest
from embit import ec, script
from embit.descriptor.taptree import TapLeaf, TapTree, _tweak_helper


MODULES = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if MODULES not in sys.path:
    sys.path.insert(0, MODULES)

if not hasattr(builtins, 'const'):
    builtins.const = lambda value: value
sys.modules.setdefault('public_constants', types.SimpleNamespace(
    AF_P2SH=8, AF_P2WSH=14, AF_P2WSH_P2SH=26))

from descriptor import append_checksum  # noqa: E402
from policy_errors import (PolicyMismatchError, PolicyParseError,  # noqa: E402
                           PolicyResourceError, PolicyTypeError)
from wallet_policy import (MiniscriptPolicy,  # noqa: E402
                           descriptor_to_policy_template)


XPUB = ('xpub6Br37sWxruYfT8ASpCjVHKGwgdnYFEn98DwiN76i2oyY6fgH1LAPmmDcF46x'
        'jxJr22gw4jmVjTE2E3URMnRPEPYyo1zoPSUba563ESMXCeb')
KEY_INFO = "[6738736c/86'/0'/0']" + XPUB
INTERNAL_KEY = bytes.fromhex(
    '79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798')
OWNED_KEY = bytes.fromhex(
    '1b84c5567b126440995d3ed5aaba0565d71e1834604819ff9c17f5e9d5dd078f')
FOREIGN_KEY = bytes.fromhex(
    'c6047f9441ed7d6d3045406e95c07cd85c778e4b8cef3ca7abac09b95c709ee5')
MY_XFP = int.from_bytes(bytes.fromhex('6738736c'), 'little')


class StubChain:
    ctype = 'BTC'

    @staticmethod
    def render_address(script_pubkey):
        return 'tr-' + script_pubkey.hex()


class FakeNode:
    def __init__(self, xpub, depth):
        self.xpub = xpub
        self._depth = depth
        self.path = []

    def depth(self):
        return self._depth

    def derive(self, value, public=False):
        assert public
        self.path.append(value)

    def public_key(self):
        digest = hashlib.sha256((self.xpub + repr(self.path)).encode()).digest()
        return bytes([2 + (digest[0] & 1)]) + digest


class DerivationChain(StubChain):
    @staticmethod
    def deserialize_node(xpub, address_format):
        assert address_format == 8
        return FakeNode(xpub, 3)


def make_policy(template=None):
    template = template or 'tr({},pk(@0/**))'.format(INTERNAL_KEY.hex())
    return MiniscriptPolicy('Tap Recovery', 'BTC', template, (KEY_INFO,), (0,))


def test_single_leaf_derivation_matches_embit_independently():
    policy = make_policy()
    derived = policy.derive(0, 0, StubChain(), lambda *_: OWNED_KEY)

    embit_leaf = TapLeaf.from_string('pk({})'.format(OWNED_KEY.hex()))
    embit_tree = TapTree(embit_leaf)
    embit_internal = ec.PublicKey.from_xonly(INTERNAL_KEY)
    embit_info, embit_root = _tweak_helper(embit_tree.tree)

    assert derived.tap_leaves[0].script == embit_leaf.miniscript.compile()
    assert derived.merkle_root == embit_root
    assert derived.script_pubkey == script.p2tr(embit_internal, embit_tree).data
    assert derived.tap_leaves[0].leaf_hash == embit_root
    parity = derived.tap_leaves[0].control_block[0] & 1
    assert derived.tap_leaves[0].control_block == \
        bytes([0xc0 | parity]) + INTERNAL_KEY + embit_info[0][1]
    assert derived.tap_tree == b'\x00\xc0' + \
        script.Script(embit_leaf.miniscript.compile()).serialize()


def test_two_leaf_merkle_paths_and_depth_encoding_match_embit():
    second = KEY_INFO.replace(XPUB[-1], '1')
    policy = MiniscriptPolicy(
        'Two Leaves', 'BTC',
        'tr({},{{pk(@0/**),pk(@1/**)}})'.format(INTERNAL_KEY.hex()),
        (KEY_INFO, second), (0,))
    derived = policy.derive(
        0, 0, StubChain(),
        lambda key_index, *_: OWNED_KEY if key_index == 0 else FOREIGN_KEY)

    left = TapLeaf.from_string('pk({})'.format(OWNED_KEY.hex()))
    right = TapLeaf.from_string('pk({})'.format(FOREIGN_KEY.hex()))
    embit_tree = TapTree((TapTree(left), TapTree(right)))
    embit_info, embit_root = _tweak_helper(embit_tree.tree)
    embit_internal = ec.PublicKey.from_xonly(INTERNAL_KEY)

    assert derived.merkle_root == embit_root
    assert derived.script_pubkey == script.p2tr(embit_internal, embit_tree).data
    assert [leaf.depth for leaf in derived.tap_leaves] == [1, 1]
    for position, leaf in enumerate(derived.tap_leaves):
        assert leaf.control_block[33:] == embit_info[position][1]
    assert derived.tap_tree == (
        b'\x01\xc0' + script.Script(left.miniscript.compile()).serialize() +
        b'\x01\xc0' + script.Script(right.miniscript.compile()).serialize())


def test_taproot_policy_profile_rejects_unsafe_or_ambiguous_templates():
    with pytest.raises(PolicyParseError, match='script leaf'):
        MiniscriptPolicy('Bad', 'BTC', 'tr(@0/**,pk(@1/**))',
                         (KEY_INFO, KEY_INFO.replace(XPUB[-1], '1')), (0,))
    with pytest.raises(PolicyTypeError, match='pk_h'):
        make_policy('tr({},pkh(@0/**))'.format(INTERNAL_KEY.hex()))
    with pytest.raises(PolicyTypeError, match='multi is only'):
        make_policy('tr({},multi(1,@0/**))'.format(INTERNAL_KEY.hex()))
    with pytest.raises(PolicyParseError, match='repeated'):
        make_policy('tr({},{{pk(@0/**),pk(@0/**)}})'.format(INTERNAL_KEY.hex()))
    too_deep = 'pk(@0/**)'
    for _ in range(6):
        too_deep = '{{{},pk(@0/<2;3>/*)}}'.format(too_deep)
    with pytest.raises((PolicyParseError, PolicyResourceError)):
        make_policy('tr({},{})'.format(INTERNAL_KEY.hex(), too_deep))


def test_multi_a_is_compiled_only_for_tapscript():
    second = KEY_INFO.replace(XPUB[-1], '1')
    policy = MiniscriptPolicy(
        'Threshold', 'BTC',
        'tr({},multi_a(1,@0/**,@1/**))'.format(INTERNAL_KEY.hex()),
        (KEY_INFO, second), (0,))
    derived = policy.derive(
        0, 2, StubChain(),
        lambda key_index, *_: OWNED_KEY if key_index == 0 else INTERNAL_KEY)
    assert derived.tap_leaves[0].script == (
        b'\x20' + OWNED_KEY + b'\xac\x20' + INTERNAL_KEY + b'\xba\x51\x9c')


def test_full_taproot_descriptor_converts_to_bip388_template():
    descriptor = 'tr({},pk({}/<0;1>/*))'.format(INTERNAL_KEY.hex(), KEY_INFO)
    template, keys = descriptor_to_policy_template(append_checksum(descriptor))
    assert template == 'tr({},pk(@0/<0;1>/*))'.format(INTERNAL_KEY.hex())
    assert keys == (KEY_INFO,)


def test_exact_bip371_input_match_and_immutable_spend_plan():
    policy = make_policy()
    chain = DerivationChain()
    derived, paths, _, hashes = policy._derive_taproot_with_paths(0, 12, chain)
    leaf = derived.tap_leaves[0]
    subpaths = {key: (path, hashes[key]) for key, path in paths.items()}
    leaf_scripts = {leaf.control_block: leaf.script + b'\xc0'}
    plan = policy.make_taproot_spend_plan(
        3, subpaths, derived.script_pubkey, leaf_scripts,
        derived.internal_key, derived.merkle_root, chain, MY_XFP, 0)

    assert plan.script_context == 'tapscript'
    assert plan.tapleaf_hash == leaf.leaf_hash
    assert plan.control_block == leaf.control_block
    assert plan.assert_tapscript_scope(
        3, subpaths, derived.script_pubkey, leaf_scripts,
        derived.internal_key, derived.merkle_root, 0, plan.expected_pubkey)
    with pytest.raises(AttributeError, match='immutable'):
        plan.tapleaf_hash = bytes(32)

    bad_hashes = dict(subpaths)
    key = next(iter(bad_hashes))
    bad_hashes[key] = (bad_hashes[key][0], (bytes(32),))
    bad_leaf = {leaf.control_block[:-1] + bytes([leaf.control_block[-1] ^ 1]):
                leaf.script + b'\xc0'}
    mutations = (
        (bad_hashes, derived.script_pubkey, leaf_scripts,
         derived.internal_key, derived.merkle_root),
        (subpaths, bytes(34), leaf_scripts,
         derived.internal_key, derived.merkle_root),
        (subpaths, derived.script_pubkey, bad_leaf,
         derived.internal_key, derived.merkle_root),
        (subpaths, derived.script_pubkey, leaf_scripts,
         OWNED_KEY, derived.merkle_root),
        (subpaths, derived.script_pubkey, leaf_scripts,
         derived.internal_key, bytes(32)),
    )
    for mutation in mutations:
        with pytest.raises(PolicyMismatchError, match='do not match'):
            policy.make_taproot_spend_plan(
                3, mutation[0], mutation[1], mutation[2], mutation[3],
                mutation[4], chain, MY_XFP, 0)


def test_spend_plan_selects_only_the_leaf_containing_passports_key():
    second = KEY_INFO.replace(XPUB[-1], '1')
    policy = MiniscriptPolicy(
        'Leaf Choice', 'BTC',
        'tr({},{{pk(@0/**),pk(@1/**)}})'.format(INTERNAL_KEY.hex()),
        (KEY_INFO, second), (0,))
    chain = DerivationChain()
    derived, paths, _, hashes = policy._derive_taproot_with_paths(0, 9, chain)
    subpaths = {key: (path, hashes[key]) for key, path in paths.items()}
    owned_leaf, foreign_leaf = derived.tap_leaves
    plan = policy.make_taproot_spend_plan(
        0, subpaths, derived.script_pubkey,
        {owned_leaf.control_block: owned_leaf.script + b'\xc0'},
        derived.internal_key, derived.merkle_root, chain, MY_XFP, 0)
    assert plan.tapleaf_hash == owned_leaf.leaf_hash
    with pytest.raises(PolicyMismatchError):
        policy.make_taproot_spend_plan(
            0, subpaths, derived.script_pubkey,
            {foreign_leaf.control_block: foreign_leaf.script + b'\xc0'},
            derived.internal_key, derived.merkle_root, chain, MY_XFP, 0)


def test_change_requires_exact_internal_key_tree_paths_and_script():
    policy = make_policy()
    chain = DerivationChain()
    derived, paths, _, hashes = policy._derive_taproot_with_paths(1, 4, chain)
    subpaths = {key: (path, hashes[key]) for key, path in paths.items()}
    assert policy.match_taproot_change(
        subpaths, derived.script_pubkey, derived.internal_key,
        derived.tap_tree, chain, MY_XFP).branch == 1
    with pytest.raises(PolicyMismatchError):
        policy.match_taproot_change(
            subpaths, derived.script_pubkey, derived.internal_key,
            None, chain, MY_XFP)


def test_dynamic_internal_key_is_recorded_as_key_path_only_metadata():
    foreign = KEY_INFO.replace(XPUB[-1], '1')
    policy = MiniscriptPolicy(
        'Key Path Warning', 'BTC', 'tr(@0/**,pk(@1/**))',
        (foreign, KEY_INFO), (1,))
    derived, paths, indexes, hashes = policy._derive_taproot_with_paths(
        0, 1, DerivationChain())
    internal_pubkey = next(key for key, index in indexes.items() if index == 0)
    leaf_pubkey = next(key for key, index in indexes.items() if index == 1)
    assert hashes[internal_pubkey] == ()
    assert hashes[leaf_pubkey] == (derived.tap_leaves[0].leaf_hash,)
    assert 'can spend by key path' in policy.format_overview()
