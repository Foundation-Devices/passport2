# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import sys

import pytest

MODULES = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if MODULES not in sys.path:
    sys.path.insert(0, MODULES)

import wallet_policy  # noqa: E402
from policy_errors import UnsupportedPolicyError  # noqa: E402
from policy_transport import decode_policy_transport, encode_policy_transport  # noqa: E402
from test_wallet_policy import DerivationChain, FakeSettings, OwnedNode, StubChain  # noqa: E402
from test_wallet_policy_taproot import KEY_INFO, MY_XFP, make_policy  # noqa: E402
from wallet_policy import (MiniscriptPolicy, WalletPolicyRegistry,  # noqa: E402
                           validate_backup_policy_records)


@pytest.fixture
def experimental_policy(monkeypatch):
    assert not wallet_policy.ENABLE_TAPROOT_POLICIES
    with monkeypatch.context() as enabled:
        enabled.setattr(wallet_policy, 'ENABLE_TAPROOT_POLICIES', True)
        policy = make_policy()
        record = policy.serialize()
        transport = encode_policy_transport(policy)
    return policy, record, transport


@pytest.mark.parametrize('transport_kind', ['descriptor', 'json', 'bytes', 'bytearray'])
def test_release_rejects_policy_import(experimental_policy, transport_kind):
    policy, _, transport = experimental_policy
    payload = {'descriptor': policy.full_descriptor(), 'json': transport,
               'bytes': transport.encode(), 'bytearray': bytearray(transport.encode())}[transport_kind]
    with pytest.raises(UnsupportedPolicyError, match='not enabled in this release'):
        decode_policy_transport(payload, DerivationChain(), MY_XFP,
                                lambda path: OwnedNode(KEY_INFO.split(']')[1]))


def test_release_rejects_backup_and_existing_records(experimental_policy):
    _, record, _ = experimental_policy
    with pytest.raises(UnsupportedPolicyError):
        MiniscriptPolicy.deserialize(record)
    with pytest.raises(UnsupportedPolicyError):
        validate_backup_policy_records([record], '6738736c', None, None)
    settings = FakeSettings()
    settings.set('wallet_policies', [record])
    registry = WalletPolicyRegistry(settings)
    assert list(registry.iter_policies()) == []
    assert len(registry.invalid_records) == 1
    assert registry.get(record['id']) is None
    assert settings.get('wallet_policies') == [record]


def test_release_rejects_cached_policy_operations(experimental_policy):
    policy, _, _ = experimental_policy
    settings = FakeSettings()
    with pytest.raises(UnsupportedPolicyError):
        WalletPolicyRegistry(settings).save(policy)
    assert settings.get('wallet_policies') is None
    with pytest.raises(UnsupportedPolicyError):
        policy.derive(0, 0, StubChain())
    with pytest.raises(UnsupportedPolicyError):
        policy.match_taproot_change({}, b'', None, None, StubChain(), MY_XFP)
    with pytest.raises(UnsupportedPolicyError):
        policy.make_taproot_spend_plan(0, {}, b'', {}, None, None, StubChain(), MY_XFP, 0)
