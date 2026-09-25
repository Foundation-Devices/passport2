# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import json
import sys

import pytest

MODULES = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if MODULES not in sys.path:
    sys.path.insert(0, MODULES)

from policy_errors import UnsupportedPolicyError  # noqa: E402
from policy_transport import decode_policy_transport  # noqa: E402
from test_wallet_policy import DerivationChain, FakeSettings, OwnedNode, KEY_INFO  # noqa: E402
from descriptor import append_checksum  # noqa: E402
from wallet_policy import (MiniscriptPolicy, WalletPolicyRegistry,  # noqa: E402
                           validate_backup_policy_records)


MY_XFP = int.from_bytes(bytes.fromhex('6738736c'), 'little')
TEMPLATE = 'tr(79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798,pk(@0/**))'


@pytest.fixture
def experimental_policy():
    # Historical experimental records must stay unavailable after removing
    # their implementation, without deleting the user's stored data.
    record = {'v': 1, 'id': 'unsupported-taproot-policy', 'n': 'Tap Recovery',
              'net': 'BTC', 't': TEMPLATE, 'k': [KEY_INFO], 'o': [0]}
    transport = json.dumps({'format': 'passport-wallet-policy', 'version': 1,
                            'name': record['n'], 'network': 'BTC',
                            'template': TEMPLATE, 'keys': [KEY_INFO]})
    descriptor = append_checksum(TEMPLATE.replace('@0', KEY_INFO))
    return descriptor, record, transport


@pytest.mark.parametrize('transport_kind', ['descriptor', 'json', 'bytes', 'bytearray'])
def test_release_rejects_policy_import(experimental_policy, transport_kind):
    descriptor, _, transport = experimental_policy
    payload = {'descriptor': descriptor, 'json': transport,
               'bytes': transport.encode(), 'bytearray': bytearray(transport.encode())}[transport_kind]
    with pytest.raises(UnsupportedPolicyError, match='wsh'):
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


@pytest.mark.parametrize('template', [TEMPLATE, 'tr(@0/**,pk(@1/**))'])
def test_taproot_policy_construction_is_unsupported(template):
    with pytest.raises(UnsupportedPolicyError):
        MiniscriptPolicy('Unsupported', 'BTC', template, [KEY_INFO], [0])
