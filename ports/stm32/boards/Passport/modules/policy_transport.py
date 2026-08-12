# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Versioned QR/microSD transport for registered wallet policies."""

try:
    import ujson as json
except ImportError:  # pragma: no cover - CPython host tests
    import json

try:
    from ubinascii import hexlify
except ImportError:  # pragma: no cover - CPython host tests
    from binascii import hexlify

from policy_errors import PolicyMismatchError, PolicyParseError, PolicyResourceError
from wallet_policy import (KeyInfo, MiniscriptPolicy,
                           descriptor_to_policy_template)


TRANSPORT_FORMAT = 'passport-wallet-policy'
TRANSPORT_VERSION = 1
MAX_TRANSPORT_LENGTH = 4096
ADDRESS_FORMAT = 'passport-address-verification'
ADDRESS_RESPONSE_FORMAT = 'passport-address-verification-response'
REGISTRATION_FORMAT = 'passport-policy-registration'
MAX_ADDRESS_INDEX = 0x7fffffff


def bounded_transport_read(fd):
    """Bound a policy/address microSD read before allocating its contents."""
    return fd.read(MAX_TRANSPORT_LENGTH + 1)


def _fingerprint_text(master_xfp):
    return hexlify(master_xfp.to_bytes(4, 'little')).decode('ascii')


def discover_owned_key(keys, chain, master_xfp, derive_node):
    expected_fingerprint = _fingerprint_text(master_xfp)
    matches = []
    from public_constants import AF_P2SH
    for index, key in enumerate(keys):
        if key.fingerprint != expected_fingerprint:
            continue
        node = derive_node(key.path)
        try:
            if chain.serialize_public(node, AF_P2SH) == key.xpub:
                matches.append(index)
        finally:
            try:
                from stash import blank_object
                blank_object(node)
            except ImportError:  # pragma: no cover - CPython host tests
                pass
    if len(matches) != 1:
        raise PolicyMismatchError(
            'Policy must contain exactly one extended key belonging to this Passport')
    return tuple(matches)


def _infer_standard_xpub_network(keys):
    networks = set()
    for key in keys:
        if key.xpub.startswith('xpub'):
            networks.add('BTC')
        elif key.xpub.startswith('tpub'):
            networks.add('TBTC')
    if len(networks) > 1:
        raise PolicyParseError('Wallet policy mixes mainnet and testnet extended keys')
    return next(iter(networks)) if networks else None


def _network_mismatch_message(network):
    name = 'Bitcoin mainnet' if network == 'BTC' else 'Bitcoin Testnet'
    return 'This wallet is for {}. Switch Passport to that network before importing.'.format(name)


def _transport_text(data, invalid_utf8_message):
    # Foundation's UR `bytes` registry binding unwraps to a MicroPython
    # bytearray backed by the decoded value. microSD reads return bytes. Treat
    # both transports identically before applying the bounded text parser.
    if isinstance(data, bytearray):
        data = bytes(data)
    if isinstance(data, bytes):
        try:
            return data.decode('utf-8')
        except UnicodeError:
            raise PolicyParseError(invalid_utf8_message)
    return data


def decode_policy_transport(data, chain, master_xfp, derive_node,
                            default_name='Wallet Policy'):
    data = _transport_text(data, 'Wallet policy file is not UTF-8 text')
    if not isinstance(data, str):
        raise PolicyParseError('Wallet policy transport must be text')
    data = data.strip()
    if not data or len(data) > MAX_TRANSPORT_LENGTH:
        raise PolicyResourceError('Wallet policy transport is empty or too large')

    policy_id = None
    if data.startswith('{'):
        try:
            envelope = json.loads(data)
        except BaseException:
            raise PolicyParseError('Wallet policy JSON is invalid')
        if not isinstance(envelope, dict):
            raise PolicyParseError('Wallet policy JSON must be an object')
        if envelope.get('format') != TRANSPORT_FORMAT or envelope.get('version') != TRANSPORT_VERSION:
            raise PolicyParseError('Unsupported wallet policy transport version')
        name = envelope.get('name') or default_name
        network = envelope.get('network')
        template = envelope.get('template')
        raw_keys = envelope.get('keys')
        if not isinstance(raw_keys, list):
            raise PolicyParseError('Wallet policy key vector is missing')
        keys = tuple(KeyInfo.parse(value) for value in raw_keys)
        policy_id = envelope.get('policy_id')
    else:
        name = default_name
        template, raw_keys = descriptor_to_policy_template(data, require_checksum=True)
        keys = tuple(KeyInfo.parse(value) for value in raw_keys)
        network = _infer_standard_xpub_network(keys) or getattr(chain, 'ctype', None)

    if network != getattr(chain, 'ctype', None):
        raise PolicyMismatchError(_network_mismatch_message(network))
    owned = discover_owned_key(keys, chain, master_xfp, derive_node)
    policy = MiniscriptPolicy(name, network, template, keys, owned)
    policy.validate_extended_keys(chain)
    policy.verify_owned_key(chain, derive_node)
    if policy_id is not None and policy_id != policy.policy_id:
        raise PolicyParseError('Transport policy identity does not match its contents')
    return policy


def encode_policy_transport(policy):
    return json.dumps({
        'format': TRANSPORT_FORMAT,
        'version': TRANSPORT_VERSION,
        'name': policy.name,
        'network': policy.network,
        'template': policy.template,
        'keys': [key.canonical() for key in policy.keys],
        'policy_id': policy.policy_id,
    })


def encode_registration_ack(policy, fingerprint):
    return json.dumps({
        'format': REGISTRATION_FORMAT,
        'version': TRANSPORT_VERSION,
        'policy_id': policy.policy_id,
        'descriptor_checksum': policy.descriptor_check().lower(),
        'fingerprint': fingerprint.lower(),
        'registered': True,
    })


def decode_address_request(data, chain, registry, expected_policy_id=None):
    data = _transport_text(data, 'Address verification request is not UTF-8 text')
    if not isinstance(data, str) or not data or len(data) > MAX_TRANSPORT_LENGTH:
        raise PolicyResourceError('Address verification request is empty or too large')
    try:
        request = json.loads(data)
    except BaseException:
        raise PolicyParseError('Address verification request JSON is invalid')
    expected_fields = {
        'format', 'version', 'network', 'policy_id',
        'descriptor_checksum', 'branch', 'index'}
    if not isinstance(request, dict) or set(request.keys()) != expected_fields:
        raise PolicyParseError('Address verification request fields are invalid')
    if request.get('format') != ADDRESS_FORMAT or request.get('version') != TRANSPORT_VERSION:
        raise PolicyParseError('Unsupported address verification request version')
    network = request.get('network')
    if network != getattr(chain, 'ctype', None):
        raise PolicyMismatchError(_network_mismatch_message(network))
    policy_id = request.get('policy_id')
    if expected_policy_id is not None and policy_id != expected_policy_id:
        raise PolicyMismatchError('Address request is for a different wallet policy')
    policy = registry.get(policy_id)
    if policy is None:
        raise PolicyMismatchError('Wallet policy is not registered on this Passport')
    checksum = request.get('descriptor_checksum')
    if not isinstance(checksum, str) or checksum.lower() != policy.descriptor_check().lower():
        raise PolicyMismatchError('Policy checksum does not match the registered wallet')
    branch = request.get('branch')
    index = request.get('index')
    if branch not in (0, 1) or isinstance(branch, bool):
        raise PolicyParseError('Address branch must be receive (0) or change (1)')
    if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index <= MAX_ADDRESS_INDEX:
        raise PolicyParseError('Address index is outside the supported range')
    derived = policy.derive(branch, index, chain)
    if not derived.address:
        raise PolicyMismatchError('Passport could not derive this policy address')
    return request, policy, derived.address


def encode_address_response(request, address, fingerprint):
    return json.dumps({
        'format': ADDRESS_RESPONSE_FORMAT,
        'version': TRANSPORT_VERSION,
        'network': request['network'],
        'policy_id': request['policy_id'],
        'descriptor_checksum': request['descriptor_checksum'].lower(),
        'branch': request['branch'],
        'index': request['index'],
        'address': address,
        'fingerprint': fingerprint.lower(),
    })
