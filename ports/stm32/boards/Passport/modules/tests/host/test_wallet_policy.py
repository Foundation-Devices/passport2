# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

import hashlib
import builtins
import os
import sys
import types

import pytest


MODULES = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if MODULES not in sys.path:
    sys.path.insert(0, MODULES)

if not hasattr(builtins, 'const'):
    builtins.const = lambda value: value
sys.modules.setdefault('public_constants', types.SimpleNamespace(
    AF_P2SH=8, AF_P2WSH=14, AF_P2WSH_P2SH=26))

from descriptor import append_checksum, split_checksum  # noqa: E402
from policy_errors import (PolicyMismatchError, PolicyParseError,  # noqa: E402
                           PolicyResourceError, PolicyTypeError)
from wallet_policy import (KeyInfo, MiniscriptPolicy,  # noqa: E402
                           WalletPolicyRegistry,
                           descriptor_to_policy_template)
from policy_transport import (decode_policy_transport,  # noqa: E402
                              encode_policy_transport)


XPUB = ('xpub6Br37sWxruYfT8ASpCjVHKGwgdnYFEn98DwiN76i2oyY6fgH1LAPmmDcF46x'
        'jxJr22gw4jmVjTE2E3URMnRPEPYyo1zoPSUba563ESMXCeb')
KEY_INFO = "[6738736c/84'/0'/0']" + XPUB
PUBKEY = bytes.fromhex(
    '031b84c5567b126440995d3ed5aaba0565d71e1834604819ff9c17f5e9d5dd078f')


class StubChain:
    ctype = 'BTC'

    @staticmethod
    def p2sh_address(addr_format, witness_script):
        return 'test-address-' + hashlib.sha256(witness_script).hexdigest()[:8]


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

    @staticmethod
    def serialize_public(node, address_format):
        assert address_format == 8
        return node.xpub


class OwnedNode:
    def __init__(self, xpub):
        self.xpub = xpub


class FakeSettings:
    def __init__(self, maximum=8192 - 32):
        self.current = {'_revision': 1}
        self.temporary_settings = {}
        self.temporary_mode = False
        self.max_json_len = maximum

    def get(self, key, default=None):
        return self.current.get(key, default)

    def set(self, key, value):
        self.current[key] = value


def make_policy(name='Recovery'):
    return MiniscriptPolicy(
        name,
        'BTC',
        'wsh(or_d(pk(@0/**),and_v(v:pk(@1/**),older(65535))))',
        (KEY_INFO, KEY_INFO.replace(XPUB[-1], '1')),
        (0,),
    )


def convert_xpub_version(xpub, version):
    alphabet = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
    number = 0
    for char in xpub:
        number = number * 58 + alphabet.index(char)
    raw = number.to_bytes((number.bit_length() + 7) // 8, 'big')
    raw = b'\0' * (len(xpub) - len(xpub.lstrip('1'))) + raw
    payload = version + raw[4:-4]
    checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    number = int.from_bytes(payload + checksum, 'big')
    encoded = ''
    while number:
        number, remainder = divmod(number, 58)
        encoded = alphabet[remainder] + encoded
    return '1' * (len(payload + checksum) - len((payload + checksum).lstrip(b'\0'))) + encoded


def test_descriptor_checksum_is_required_and_verified():
    body = 'wsh(pk(@0/**))'
    checksummed = append_checksum(body)
    assert split_checksum(checksummed) == (body, checksummed[-8:])
    with pytest.raises(ValueError, match='required'):
        split_checksum(body)
    with pytest.raises(ValueError, match='does not match'):
        split_checksum(checksummed[:-1] + ('q' if checksummed[-1] != 'q' else 'p'))


def test_key_information_is_canonical_and_bounded():
    key = KeyInfo.parse(KEY_INFO)
    assert key.fingerprint == '6738736c'
    assert key.path == (0x80000054, 0x80000000, 0x80000000)
    assert key.canonical() == KEY_INFO
    assert KeyInfo.parse(KEY_INFO.replace("'", 'h')).canonical() == KEY_INFO
    with pytest.raises(PolicyParseError):
        KeyInfo.parse('[xyz/0]' + XPUB)
    with pytest.raises(PolicyParseError):
        KeyInfo.parse('[6738736c/00]' + XPUB)


@pytest.mark.parametrize('name', (' Recovery', 'Recovery ', 'Bad\nName', 'Bad\x00Name'))
def test_policy_name_rejects_ambiguous_display_text(name):
    with pytest.raises(PolicyParseError, match='printable ASCII'):
        MiniscriptPolicy(name, 'BTC', 'wsh(pk(@0/**))', (KEY_INFO,), (0,))


def test_full_multipath_descriptor_converts_to_canonical_policy():
    second = KEY_INFO.replace(XPUB[-1], '1')
    full = ('wsh(or_d(pk(' + KEY_INFO + '/<0;1>/*),and_v(v:pk(' +
            second.replace("'", 'H') + '/<0;1>/*),older(65535))))')
    template, keys = descriptor_to_policy_template(append_checksum(full))
    assert template == 'wsh(or_d(pk(@0/<0;1>/*),and_v(v:pk(@1/<0;1>/*),older(65535))))'
    assert keys == (KEY_INFO, second)
    policy = MiniscriptPolicy.from_multipath_descriptor(
        'Imported', 'BTC', append_checksum(full), (0,))
    assert policy.template == template
    assert [key.canonical() for key in policy.keys] == list(keys)


@pytest.mark.parametrize('descriptor', (
    'wsh(pk(' + KEY_INFO + '/0/*))',
    'wsh(pk(' + KEY_INFO + '/<0;0>/*))',
    'wsh(pk(' + KEY_INFO + '/<0;1;2>/*))',
    'sh(wsh(pk(' + KEY_INFO + '/<0;1>/*)))',
))
def test_full_descriptor_converter_rejects_non_bip388_derivation(descriptor):
    with pytest.raises(PolicyParseError):
        descriptor_to_policy_template(append_checksum(descriptor))


def test_policy_id_is_stable_across_rename_but_contents_are_validated():
    policy = make_policy()
    renamed = policy.rename('Inheritance')
    assert renamed.policy_id == policy.policy_id
    record = policy.serialize()
    assert MiniscriptPolicy.deserialize(record).policy_id == policy.policy_id
    record['t'] = 'wsh(pk(@0/**))'
    with pytest.raises(PolicyParseError):
        MiniscriptPolicy.deserialize(record)


def test_local_key_names_are_migration_safe_and_do_not_change_policy_identity():
    policy = make_policy()
    legacy_record = policy.serialize()
    assert 'kn' not in legacy_record
    migrated = MiniscriptPolicy.deserialize(legacy_record)
    assert migrated.key_names == ('', '')

    named = migrated.name_keys(('', 'Family Recovery'))
    assert named.policy_id == policy.policy_id
    assert named.serialize()['kn'] == ['', 'Family Recovery']
    assert MiniscriptPolicy.deserialize(named.serialize()).key_names == (
        '', 'Family Recovery')
    with pytest.raises(PolicyParseError, match='printable ASCII'):
        migrated.name_key(1, ' Bad label')


def test_policy_requires_complete_placeholder_vector_in_first_use_order():
    with pytest.raises(PolicyParseError, match='@0, @1 order'):
        MiniscriptPolicy('Bad', 'BTC', 'wsh(multi(1,@1/**,@0/**))',
                         (KEY_INFO, KEY_INFO.replace(XPUB[-1], '1')), (0,))
    with pytest.raises(PolicyParseError, match='every key'):
        MiniscriptPolicy('Bad', 'BTC', 'wsh(pk(@0/**))',
                         (KEY_INFO, KEY_INFO.replace(XPUB[-1], '1')), (0,))


def test_phase_a_rejects_two_signing_keys_from_owned_xpub():
    with pytest.raises(PolicyParseError, match='exactly one Passport signing key'):
        MiniscriptPolicy(
            'Bad', 'BTC',
            'wsh(multi(1,@0/<0;1>/*,@0/<2;3>/*,@1/**))',
            (KEY_INFO, KEY_INFO.replace(XPUB[-1], '1')), (0,))


def test_policy_derivation_and_exact_script_matching():
    policy = MiniscriptPolicy('Simple', 'BTC', 'wsh(pk(@0/**))', (KEY_INFO,), (0,))
    chain = StubChain()
    derived = policy.derive(0, 7, chain, lambda *_: PUBKEY)
    assert derived.witness_script == bytes.fromhex(
        '21031b84c5567b126440995d3ed5aaba0565d71e1834604819ff9c17f5e9d5dd078fac')
    assert derived.script_pubkey == b'\x00\x20' + hashlib.sha256(derived.witness_script).digest()
    assert policy.match_scripts(0, 7, chain, derived.script_pubkey,
                                derived.witness_script, lambda *_: PUBKEY) is not None
    with pytest.raises(PolicyMismatchError, match='UTXO'):
        policy.match_scripts(0, 7, chain, bytes(34), derived.witness_script,
                             lambda *_: PUBKEY)
    with pytest.raises(PolicyMismatchError, match='witness'):
        policy.match_scripts(0, 7, chain, derived.script_pubkey, b'wrong',
                             lambda *_: PUBKEY)


def test_psbt_derivations_produce_immutable_spend_plan():
    policy = make_policy()
    chain = DerivationChain()
    derived, expected_paths, _ = policy._derive_with_paths(0, 12, chain)
    plan = policy.make_spend_plan(3, expected_paths, derived.script_pubkey,
                                  derived.witness_script, chain,
                                  int.from_bytes(bytes.fromhex('6738736c'), 'little'), 1)
    assert plan.policy_id == policy.policy_id
    assert plan.input_index == 3
    assert plan.branch == 0
    assert plan.address_index == 12
    assert plan.script_context == 'p2wsh'
    assert plan.timelocks == (('older', 65535),)
    assert plan.expected_pubkey in expected_paths

    wrong_paths = dict(expected_paths)
    wrong_key = next(iter(wrong_paths))
    wrong_paths[wrong_key] = list(wrong_paths[wrong_key][:-1]) + [13]
    with pytest.raises(PolicyMismatchError, match='do not match'):
        policy.make_spend_plan(3, wrong_paths, derived.script_pubkey,
                               derived.witness_script, chain,
                               int.from_bytes(bytes.fromhex('6738736c'), 'little'), 1)


def test_spend_plan_rejects_non_all_sighash():
    policy = make_policy()
    with pytest.raises(PolicyMismatchError, match='SIGHASH_ALL'):
        policy.make_spend_plan(0, {}, bytes(34), b'', DerivationChain(),
                               int.from_bytes(bytes.fromhex('6738736c'), 'little'), 0)


def test_network_mismatch_fails_closed():
    policy = MiniscriptPolicy('Simple', 'TBTC', 'wsh(pk(@0/**))', (KEY_INFO,), (0,))
    with pytest.raises(PolicyMismatchError, match='network'):
        policy.derive(0, 0, StubChain(), lambda *_: PUBKEY)


def test_relative_timelock_rejects_values_that_consensus_would_mask():
    with pytest.raises(PolicyTypeError, match='BIP68 relative timelock limit'):
        MiniscriptPolicy(
            'Too Long', 'BTC',
            'wsh(or_d(pk(@0/**),and_v(v:pk(@1/**),older(78894))))',
            (KEY_INFO, KEY_INFO.replace(XPUB[-1], '1')), (0,))


def test_registry_validates_records_and_quarantines_corruption():
    settings = FakeSettings()
    registry = WalletPolicyRegistry(settings)
    policy = make_policy()
    registry.save(policy)
    assert registry.get(policy.policy_id).name == policy.name
    with pytest.raises(PolicyParseError, match='already'):
        registry.save(policy)

    settings.current['wallet_policies'].append({'v': 99})
    assert [item.policy_id for item in registry.iter_policies()] == [policy.policy_id]
    assert len(registry.invalid_records) == 1

    registry.rename(policy.policy_id, 'New Name')
    assert registry.get(policy.policy_id).name == 'New Name'
    registry.rename_keys(policy.policy_id, ('', 'Family Recovery'))
    assert registry.get(policy.policy_id).key_names == ('', 'Family Recovery')
    registry.delete(policy.policy_id)
    assert registry.get(policy.policy_id) is None


def test_registry_preserves_settings_headroom():
    settings = FakeSettings(maximum=900)
    registry = WalletPolicyRegistry(settings)
    with pytest.raises(PolicyResourceError, match='space'):
        registry.save(make_policy())


def test_policy_transport_round_trip_rediscovers_owned_key():
    policy = make_policy()
    encoded = encode_policy_transport(policy)
    decoded = decode_policy_transport(
        encoded, DerivationChain(),
        int.from_bytes(bytes.fromhex('6738736c'), 'little'),
        lambda path: OwnedNode(XPUB))
    assert decoded.policy_id == policy.policy_id
    assert decoded.owned_key_indexes == (0,)


def test_policy_transport_rejects_tampered_identity():
    policy = make_policy()
    encoded = encode_policy_transport(policy).replace(policy.policy_id, '00' * 32)
    with pytest.raises(PolicyParseError, match='identity'):
        decode_policy_transport(
            encoded, DerivationChain(),
            int.from_bytes(bytes.fromhex('6738736c'), 'little'),
            lambda path: OwnedNode(XPUB))


def test_raw_descriptor_reports_testnet_mismatch_before_key_ownership():
    tpub = convert_xpub_version(XPUB, bytes.fromhex('043587cf'))
    descriptor = append_checksum('wsh(pk({}/**))'.format(
        KEY_INFO.replace(XPUB, tpub).replace("/84'/0'/0'", "/84'/1'/0'")))
    with pytest.raises(PolicyMismatchError, match='Bitcoin Testnet.*Switch Passport'):
        decode_policy_transport(
            descriptor, DerivationChain(),
            int.from_bytes(bytes.fromhex('6738736c'), 'little'),
            lambda path: (_ for _ in ()).throw(AssertionError('ownership ran first')))


def test_transport_does_not_treat_local_signer_names_as_coordinator_data():
    policy = make_policy().name_keys(('', 'Family Recovery'))
    encoded = encode_policy_transport(policy)
    assert 'Family Recovery' not in encoded
