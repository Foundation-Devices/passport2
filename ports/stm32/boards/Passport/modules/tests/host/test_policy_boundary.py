# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

import builtins
import hashlib
import os
import sys
import types

import pytest


MODULES = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if MODULES not in sys.path:
    sys.path.insert(0, MODULES)

# Passport's frozen modules provide const as a built-in under MicroPython.
if not hasattr(builtins, 'const'):
    builtins.const = lambda value: value

sys.modules.setdefault('public_constants', types.SimpleNamespace(
    AF_P2SH=8, AF_P2WSH=14, AF_P2WSH_P2SH=26))

from policy_errors import PolicyMismatchError  # noqa: E402
from policy_multisig import StandardMultisigPolicy  # noqa: E402
from spend_plan import SpendPlan  # noqa: E402


SCRIPT = bytes.fromhex('5221' + '02' + '11' * 32 + '51ae')


class FakeChain:
    ctype = 'BTC'


class FakeMultisigWallet:
    name = 'Legacy'
    chain_type = 'BTC'
    id = 42
    chain = FakeChain()

    def __init__(self, address_format):
        self.addr_fmt = address_format

    @staticmethod
    def yield_addresses(start, count, change_idx=0):
        assert count == 1
        yield start, (), 'legacy-address', SCRIPT


@pytest.mark.parametrize('address_format, expected_script', (
    (14, b'\x00\x20' + hashlib.sha256(SCRIPT).digest()),
    (26, b'\xa9\x14' + hashlib.new(
        'ripemd160', hashlib.sha256(b'\x00\x20' + hashlib.sha256(SCRIPT).digest()).digest()
    ).digest() + b'\x87'),
    (8, b'\xa9\x14' + hashlib.new('ripemd160', hashlib.sha256(SCRIPT).digest()).digest() + b'\x87'),
))
def test_legacy_multisig_adapter_derives_exact_scriptpubkey(address_format, expected_script):
    policy = StandardMultisigPolicy(FakeMultisigWallet(address_format))
    result = policy.derive(1, 7)
    assert result.policy_id == 'legacy-multisig:42'
    assert result.branch == 1
    assert result.index == 7
    assert result.script_pubkey == expected_script
    assert policy.match_scripts(1, 7, expected_script,
                                result.witness_script, result.redeem_script) is not None
    with pytest.raises(PolicyMismatchError):
        policy.match_scripts(1, 7, bytes(len(expected_script)))


def test_spend_plan_is_immutable_after_validation():
    plan = SpendPlan('policy', 0, 0, 12, 'p2wsh', (1, 2, 3),
                     bytes(33), 1, script_pubkey=b'output',
                     witness_script=b'script')
    assert plan.address_index == 12
    with pytest.raises(AttributeError, match='immutable'):
        plan.address_index = 13


def test_spend_plan_rechecks_complete_signing_scope():
    pubkey = bytes.fromhex('02' + '11' * 32)
    path = (0x12345678, 0x80000030, 0, 4)
    plan = SpendPlan('policy', 2, 0, 4, 'p2wsh', path, pubkey, 1,
                     script_pubkey=b'output', witness_script=b'script')
    assert plan.assert_p2wsh_scope(
        2, {pubkey: path}, b'output', b'script', 1, {pubkey})

    mutations = (
        (3, {pubkey: path}, b'output', b'script', 1, {pubkey}),
        (2, {pubkey: path}, b'changed', b'script', 1, {pubkey}),
        (2, {pubkey: path}, b'output', b'changed', 1, {pubkey}),
        (2, {pubkey: path}, b'output', b'script', 0, {pubkey}),
        (2, {pubkey: path[:-1] + (5,)}, b'output', b'script', 1, {pubkey}),
        (2, {pubkey: path}, b'output', b'script', 1, {bytes(33)}),
    )
    for mutation in mutations:
        with pytest.raises(ValueError):
            plan.assert_p2wsh_scope(*mutation)


def test_spend_plan_binds_multiple_owned_signing_keys():
    first = bytes.fromhex('02' + '11' * 32)
    second = bytes.fromhex('03' + '22' * 32)
    first_path = (0x12345678, 0x80000030, 0, 4)
    second_path = (0x12345678, 0x80000030, 2, 4)
    plan = SpendPlan(
        'policy', 2, 0, 4, 'p2wsh', first_path, first, 1,
        script_pubkey=b'output', witness_script=b'script',
        owned_signing_keys=((first_path, first), (second_path, second)))
    subpaths = {first: first_path, second: second_path}
    assert plan.assert_p2wsh_scope(
        2, subpaths, b'output', b'script', 1, {first, second})
    assert plan.assert_p2wsh_scope(
        2, subpaths, b'output', b'script', 1, {second}, {first})
    with pytest.raises(ValueError, match='signing key'):
        plan.assert_p2wsh_scope(
            2, subpaths, b'output', b'script', 1, {first}, {first})
