# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Registered wallet-policy model shared by address and PSBT workflows."""

try:
    import ujson as json
except ImportError:  # pragma: no cover - CPython host tests
    import json

try:
    from ubinascii import hexlify, unhexlify
except ImportError:  # pragma: no cover - CPython host tests
    from binascii import hexlify, unhexlify

from descriptor import split_checksum
from miniscript import (MAX_KEYS, MAX_TEMPLATE_LENGTH, Parser,
                        compile_miniscript, iter_policy_keys, validate)
from policy_errors import (PolicyMismatchError, PolicyParseError,
                           PolicyResourceError, UnsupportedPolicyError, WalletPolicyError)


POLICY_FORMAT_VERSION = 1
POLICY_STORAGE_KEY = 'wallet_policies'
MAX_POLICY_NAME_LENGTH = 20
MAX_KEY_NAME_LENGTH = 20
MAX_POLICY_RECORD_LENGTH = 3072
SETTINGS_HEADROOM = 768
BASE58_CHARS = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'


def validate_backup_policy_records(records, expected_fingerprint, derive_node,
                                   chain_lookup):
    """Validate and canonicalize wallet policies restored from a backup.

    A backup may contain policies for both Bitcoin mainnet and testnet,
    regardless of the device's currently selected network.  Validate each
    policy using the network declared by that policy instead of applying the
    backup's active chain to every record.
    """
    if not isinstance(records, list):
        raise PolicyParseError('Wallet-policy backup records must be a list')

    expected_fingerprint = expected_fingerprint.lower()
    validated_records = []
    policy_ids = set()
    for record in records:
        policy = MiniscriptPolicy.deserialize(record)
        policy_chain = chain_lookup(policy.network)
        policy.validate_extended_keys(policy_chain)
        owned_key = policy.keys[policy.owned_key_indexes[0]]
        if owned_key.fingerprint != expected_fingerprint:
            raise PolicyMismatchError('Wallet policy belongs to another seed')
        policy.verify_owned_key(policy_chain, derive_node)
        if policy.policy_id in policy_ids:
            raise PolicyParseError('Duplicate wallet policy in backup')
        policy_ids.add(policy.policy_id)
        validated_records.append(policy.serialize())
    return validated_records


def _max_key_uses_per_path(node, key_index):
    """Conservatively count key uses in any one executable WSH path.

    ``or_i`` selects exactly one child at execution time, so repeated key
    expressions on opposite sides are mutually exclusive.  For every other
    fragment, summing child occurrences is deliberately conservative: a
    policy is rejected unless Passport can prove that no spending path needs
    more than one signature from its owned xpub.
    """
    if node.kind in ('pk_k', 'pk_h'):
        return 1 if node.value.index == key_index else 0
    if node.kind == 'multi':
        return sum(1 for key in node.args if key.index == key_index)
    child_counts = [_max_key_uses_per_path(child, key_index)
                    for child in node.args if hasattr(child, 'kind')]
    if node.kind == 'or_i':
        return max(child_counts) if child_counts else 0
    return sum(child_counts)


def _is_decimal(text):
    return bool(text) and all('0' <= ch <= '9' for ch in text)


def _sha256(data):
    try:
        import trezorcrypto
        return trezorcrypto.sha256(data).digest()
    except ImportError:  # pragma: no cover - CPython host tests
        import hashlib
        return hashlib.sha256(data).digest()


def _compact_size(value):
    if value < 253:
        return bytes([value])
    if value < 0x10000:
        return b'\xfd' + bytes([value & 0xff, value >> 8])
    if value < 0x100000000:
        return b'\xfe' + bytes([
            value & 0xff, (value >> 8) & 0xff,
            (value >> 16) & 0xff, (value >> 24) & 0xff,
        ])
    raise PolicyResourceError('Canonical policy field is too large')


def _encode_field(value):
    encoded = value.encode('ascii')
    return _compact_size(len(encoded)) + encoded


def _fingerprint_int(fingerprint):
    return int.from_bytes(unhexlify(fingerprint), 'little')


class KeyInfo:
    __slots__ = ('fingerprint', 'path', 'xpub')

    def __init__(self, fingerprint, path, xpub):
        self.fingerprint = fingerprint
        self.path = tuple(path)
        self.xpub = xpub

    @classmethod
    def parse(cls, text):
        if not isinstance(text, str):
            raise PolicyParseError('Key information must be text')
        try:
            text.encode('ascii')
        except UnicodeError:
            raise PolicyParseError('Key information must contain ASCII only')
        if not text.startswith('['):
            raise PolicyParseError('Key origin information is required')
        close = text.find(']')
        if close < 0:
            raise PolicyParseError('Key origin is missing closing bracket')
        origin = text[1:close]
        xpub = text[close + 1:]
        parts = origin.split('/')
        fingerprint = parts[0]
        if len(fingerprint) != 8 or any(ch not in '0123456789abcdefABCDEF' for ch in fingerprint):
            raise PolicyParseError('Key fingerprint must be exactly 8 hexadecimal characters')
        if not 100 <= len(xpub) <= 120 or any(ch not in BASE58_CHARS for ch in xpub):
            raise PolicyParseError('Extended public key encoding is invalid')

        path = []
        for element in parts[1:]:
            if not element:
                raise PolicyParseError('Key origin contains an empty path element')
            hardened = element[-1:] in ("'", 'h', 'H')
            number = element[:-1] if hardened else element
            if not _is_decimal(number) or (len(number) > 1 and number[0] == '0'):
                raise PolicyParseError('Key origin contains an invalid path element')
            if len(number) > 10 or int(number) >= 0x80000000:
                raise PolicyResourceError('Key origin path element is too large')
            value = int(number)
            if hardened:
                value |= 0x80000000
            path.append(value)
        return cls(fingerprint.lower(), path, xpub)

    def canonical(self):
        result = '[' + self.fingerprint
        for value in self.path:
            hardened = bool(value & 0x80000000)
            result += '/' + str(value & 0x7fffffff) + ("'" if hardened else '')
        return result + ']' + self.xpub


def descriptor_to_policy_template(descriptor, require_checksum=True):
    """Convert a checksummed full multipath descriptor to BIP388 form.

    Only the deliberately narrow registered-policy key grammar is accepted.  The
    resulting template is reparsed by ``MiniscriptPolicy`` before it can be
    stored or used.
    """
    body, _ = split_checksum(descriptor, require=require_checksum)
    if body.startswith('tr('):
        raise UnsupportedPolicyError('Only native SegWit (wsh) wallet policies are supported')
    if not (body.startswith('wsh(') and body.endswith(')')):
        raise PolicyParseError('Imports require a top-level wsh descriptor')
    try:
        body.encode('ascii')
    except UnicodeError:
        raise PolicyParseError('Descriptor must contain ASCII only')

    output = []
    key_values = []
    position = 0
    length = len(body)
    while position < length:
        if body[position] != '[':
            output.append(body[position])
            position += 1
            continue

        close = body.find(']', position + 1)
        if close < 0:
            raise PolicyParseError('Descriptor key origin is missing closing bracket')
        xpub_start = close + 1
        xpub_end = xpub_start
        while xpub_end < length and body[xpub_end] in BASE58_CHARS:
            xpub_end += 1
        if xpub_end == xpub_start:
            raise PolicyParseError('Descriptor key origin is not followed by an extended key')
        key_info = KeyInfo.parse(body[position:xpub_end]).canonical()

        if body[xpub_end:xpub_end + 3] == '/**':
            suffix = '/**'
            next_position = xpub_end + 3
        elif body[xpub_end:xpub_end + 2] == '/<':
            suffix_end = body.find('>/*', xpub_end + 2)
            if suffix_end < 0:
                raise PolicyParseError('Multipath key suffix is incomplete')
            branch_text = body[xpub_end + 2:suffix_end]
            branch_parts = branch_text.split(';')
            if len(branch_parts) != 2:
                raise PolicyParseError('Exactly two multipath branches are required')
            branch_values = []
            for part in branch_parts:
                if not _is_decimal(part) or (len(part) > 1 and part[0] == '0'):
                    raise PolicyParseError('Multipath branch is not canonical')
                if len(part) > 10 or int(part) >= 0x80000000:
                    raise PolicyResourceError('Multipath branch is too large')
                branch_values.append(int(part))
            if branch_values[0] == branch_values[1]:
                raise PolicyParseError('Receive and change branches must be different')
            suffix = '/<{};{}>/*'.format(branch_values[0], branch_values[1])
            next_position = suffix_end + 3
        else:
            raise PolicyParseError('Extended keys must end in /** or /<M;N>/*')

        if key_info not in key_values:
            if len(key_values) >= MAX_KEYS:
                raise PolicyResourceError('Descriptor contains too many extended keys')
            key_values.append(key_info)
        key_index = key_values.index(key_info)
        output.append('@{}{}'.format(key_index, suffix))
        position = next_position

    template = ''.join(output)
    return template, tuple(key_values)


class DerivedPolicyOutput:
    __slots__ = ('policy_id', 'branch', 'index', 'witness_script',
                 'redeem_script', 'script_pubkey', 'address')

    def __init__(self, policy_id, branch, index, witness_script,
                 script_pubkey, address, redeem_script=None):
        self.policy_id = policy_id
        self.branch = branch
        self.index = index
        self.witness_script = witness_script
        self.redeem_script = redeem_script
        self.script_pubkey = script_pubkey
        self.address = address


class MiniscriptPolicy:
    __slots__ = ('name', 'network', 'template', 'keys', 'owned_key_indexes',
                 'miniscript', 'context',
                 'policy_id', 'key_names')

    def __init__(self, name, network, template, keys, owned_key_indexes,
                 key_names=None):
        if not isinstance(name, str) or not name or len(name) > MAX_POLICY_NAME_LENGTH:
            raise PolicyParseError('Policy name must contain 1 to {} characters'.format(MAX_POLICY_NAME_LENGTH))
        try:
            name.encode('ascii')
        except UnicodeError:
            raise PolicyParseError('Policy name must contain ASCII only')
        if name != name.strip() or any(ord(ch) < 32 or ord(ch) > 126 for ch in name):
            raise PolicyParseError('Policy name must use printable ASCII without outer whitespace')
        if network not in ('BTC', 'TBTC'):
            raise PolicyParseError('Unsupported policy network')
        if not isinstance(template, str) or len(template) > MAX_TEMPLATE_LENGTH:
            raise PolicyParseError('Policy must use a bounded descriptor template')
        try:
            template.encode('ascii')
        except UnicodeError:
            raise PolicyParseError('Policy template must contain ASCII only')

        if template.startswith('wsh(') and template.endswith(')'):
            context = 'wsh'
            miniscript = Parser(template[4:-1]).parse()
            validate(miniscript, context)
            key_expressions = list(iter_policy_keys(miniscript))
        else:
            raise UnsupportedPolicyError('Only native SegWit (wsh) wallet policies are supported')

        if not 1 <= len(keys) <= MAX_KEYS:
            raise PolicyResourceError('Policy must contain between 1 and {} keys'.format(MAX_KEYS))
        parsed_keys = tuple(key if isinstance(key, KeyInfo) else KeyInfo.parse(key) for key in keys)
        canonical_keys = [key.canonical() for key in parsed_keys]
        if len(set(canonical_keys)) != len(canonical_keys):
            raise PolicyParseError('Policy key information entries must be distinct')

        indexes = [key.index for key in key_expressions]
        expected = list(range(len(parsed_keys)))
        first_seen = []
        for index in indexes:
            if index not in first_seen:
                first_seen.append(index)
        if first_seen != expected or set(indexes) != set(expected):
            raise PolicyParseError('Key placeholders must reference every key in @0, @1 order')

        owned = tuple(owned_key_indexes)
        if len(owned) != 1 or owned[0] not in expected:
            raise PolicyParseError('Policies require exactly one Passport-owned policy key')
        if _max_key_uses_per_path(miniscript, owned[0]) > 1:
            raise PolicyParseError(
                'A spending path cannot require more than one Passport signature')
        if key_names is None:
            names = ('',) * len(parsed_keys)
        else:
            names = tuple(key_names)
            if len(names) != len(parsed_keys):
                raise PolicyParseError('Policy key names do not match its key vector')
            for key_name in names:
                if not isinstance(key_name, str) or len(key_name) > MAX_KEY_NAME_LENGTH:
                    raise PolicyParseError(
                        'Key names may contain up to {} characters'.format(
                            MAX_KEY_NAME_LENGTH))
                try:
                    key_name.encode('ascii')
                except UnicodeError:
                    raise PolicyParseError('Key names must contain ASCII only')
                if key_name != key_name.strip() or any(
                        ord(char) < 32 or ord(char) > 126 for char in key_name):
                    raise PolicyParseError(
                        'Key names must use printable ASCII without outer whitespace')

        self.name = name
        self.network = network
        self.template = template
        self.keys = parsed_keys
        self.owned_key_indexes = owned
        self.miniscript = miniscript
        self.context = context
        self.key_names = names
        self.policy_id = self.calculate_id()

        record_len = len(json.dumps(self.serialize()))
        if record_len > MAX_POLICY_RECORD_LENGTH:
            raise PolicyResourceError('Serialized policy exceeds {} bytes'.format(MAX_POLICY_RECORD_LENGTH))

    @classmethod
    def from_descriptor(cls, name, network, descriptor, keys, owned_key_indexes,
                        require_checksum=True):
        body, _ = split_checksum(descriptor, require=require_checksum)
        return cls(name, network, body, keys, owned_key_indexes)

    @classmethod
    def from_multipath_descriptor(cls, name, network, descriptor,
                                  owned_key_indexes, require_checksum=True):
        template, keys = descriptor_to_policy_template(descriptor, require_checksum)
        return cls(name, network, template, keys, owned_key_indexes)

    def validate_extended_keys(self, chain):
        """Decode all xpubs and verify network, depth, and public-key uniqueness."""
        if getattr(chain, 'ctype', None) != self.network:
            raise PolicyMismatchError('Policy network does not match the active network')
        from public_constants import AF_P2SH
        public_keys = set()
        for key in self.keys:
            try:
                node = chain.deserialize_node(key.xpub, AF_P2SH)
            except BaseException:
                raise PolicyParseError('Extended public key could not be decoded for this network')
            if node.depth() != len(key.path):
                raise PolicyParseError('Extended key depth does not match its origin path')
            public_key = bytes(node.public_key())
            if public_key in public_keys:
                raise PolicyParseError('Extended public keys resolve to duplicate public keys')
            public_keys.add(public_key)
        return True

    def verify_owned_key(self, chain, derive_node):
        """Prove the declared owned xpub against the current seed.

        ``derive_node`` receives the numeric origin path and must return the
        current seed's HD node at that path.  The complete serialized xpub is
        compared; a fingerprint match alone is never sufficient.
        """
        from public_constants import AF_P2SH
        owned_index = self.owned_key_indexes[0]
        key = self.keys[owned_index]
        node = derive_node(key.path)
        try:
            derived_xpub = chain.serialize_public(node, AF_P2SH)
        finally:
            try:
                from stash import blank_object
                blank_object(node)
            except ImportError:  # pragma: no cover - CPython host tests
                pass
        if derived_xpub != key.xpub:
            raise PolicyMismatchError('Passport-owned extended key does not match the current seed')
        return True

    @classmethod
    def deserialize(cls, record):
        if not isinstance(record, dict) or record.get('v') != POLICY_FORMAT_VERSION:
            raise PolicyParseError('Unsupported wallet-policy record version')
        policy = cls(record.get('n'), record.get('net'), record.get('t'),
                     record.get('k', ()), record.get('o', ()),
                     record.get('kn'))
        stored_id = record.get('id')
        if stored_id != policy.policy_id:
            raise PolicyParseError('Stored policy identity does not match its contents')
        return policy

    def calculate_id(self):
        payload = b'Passport Wallet Policy\x00' + bytes([POLICY_FORMAT_VERSION])
        payload += _encode_field(self.network)
        payload += _encode_field(self.template)
        payload += _compact_size(len(self.keys))
        for key in self.keys:
            payload += _encode_field(key.canonical())
        return hexlify(_sha256(payload)).decode('ascii')

    def serialize(self):
        record = {
            'v': POLICY_FORMAT_VERSION,
            'id': self.policy_id,
            'n': self.name,
            'net': self.network,
            't': self.template,
            'k': [key.canonical() for key in self.keys],
            'o': list(self.owned_key_indexes),
        }
        if any(self.key_names):
            record['kn'] = list(self.key_names)
        return record

    def format_overview(self):
        # Kept as a compact compatibility entry point for callers that only
        # support one page. Import and view flows use all semantic review pages.
        return self.format_review_pages()[0]

    @staticmethod
    def _format_origin_path(path):
        result = 'm'
        for value in path:
            result += '/{}{}'.format(value & 0x7fffffff,
                                     "'" if value & 0x80000000 else '')
        return result

    def format_details(self):
        lines = ['Technical details',
                 'Full descriptor\n' + self.full_descriptor()]
        for index, key in enumerate(self.keys):
            if index in self.owned_key_indexes:
                role = 'This Passport'
            elif self.key_names[index]:
                role = self.key_names[index].replace('#', '##')
            else:
                role = 'External key'
            lines.append('Key {} - {}\nFingerprint {}\nPath {}\n{}'.format(
                index + 1, role, key.fingerprint.upper(),
                self._format_origin_path(key.path), key.xpub))
        lines.append('Internal policy ID\n' + self.policy_id)
        return '\n\n'.join(lines)

    def full_descriptor(self, with_checksum=True):
        descriptor = self.template
        # Replace higher indexes first so @1 cannot match the start of @10.
        for index in range(len(self.keys) - 1, -1, -1):
            descriptor = descriptor.replace('@{}'.format(index),
                                            self.keys[index].canonical())
        if with_checksum:
            from descriptor import append_checksum
            return append_checksum(descriptor)
        return descriptor

    def descriptor_check(self):
        return self.full_descriptor().rsplit('#', 1)[1].upper()

    def format_review_pages(self):
        from policy_display import format_review_pages
        return format_review_pages(self)

    def format_confirmation(self):
        from policy_display import format_confirmation
        return format_confirmation(self)

    def format_signing_pages(self, compatible_indexes=None):
        from policy_display import format_signing_pages
        return format_signing_pages(self, compatible_indexes)

    def rename(self, name):
        return MiniscriptPolicy(name, self.network, self.template, self.keys,
                                self.owned_key_indexes, self.key_names)

    def name_key(self, key_index, name):
        if key_index < 0 or key_index >= len(self.keys):
            raise PolicyParseError('Policy key index is outside the key vector')
        names = list(self.key_names)
        names[key_index] = name
        return MiniscriptPolicy(self.name, self.network, self.template, self.keys,
                                self.owned_key_indexes, names)

    def name_keys(self, names):
        return MiniscriptPolicy(self.name, self.network, self.template, self.keys,
                                self.owned_key_indexes, names)

    def _key_expressions(self):
        return iter_policy_keys(self.miniscript)

    def _resolver(self, chain):
        def resolve(key_index, branch, address_index):
            from public_constants import AF_P2SH
            key = self.keys[key_index]
            # AF_P2SH selects the standard xpub/tpub version rather than a
            # script-specific SLIP132 serialization.
            node = chain.deserialize_node(key.xpub, AF_P2SH)
            if node.depth() != len(key.path):
                raise PolicyMismatchError('Extended key depth does not match its origin path')
            node.derive(branch, True)
            node.derive(address_index, True)
            public_key = bytes(node.public_key())
            return public_key if self.context == 'wsh' else public_key[1:]
        return resolve

    def _derive_with_paths(self, branch, index, chain):
        """Derive the script and the exact PSBT derivation map it requires."""
        from public_constants import AF_P2SH
        expected_paths = {}
        expected_key_indexes = {}

        def resolve(key_index, child_branch, address_index):
            key = self.keys[key_index]
            node = chain.deserialize_node(key.xpub, AF_P2SH)
            if node.depth() != len(key.path):
                raise PolicyMismatchError('Extended key depth does not match its origin path')
            node.derive(child_branch, True)
            node.derive(address_index, True)
            public_key = bytes(node.public_key())
            path = [_fingerprint_int(key.fingerprint)] + list(key.path)
            path.extend((child_branch, address_index))
            if public_key in expected_paths and expected_paths[public_key] != path:
                raise PolicyMismatchError('Policy derives a repeated public key')
            expected_paths[public_key] = path
            expected_key_indexes[public_key] = key_index
            return public_key

        return self.derive(branch, index, chain, resolve), expected_paths, expected_key_indexes

    def match_derivations(self, subpaths, utxo_script_pubkey, witness_script,
                          chain, my_xfp):
        """Resolve branch/index and exactly match a P2WSH PSBT scope."""
        if self.context != 'wsh':
            raise PolicyMismatchError('P2WSH derivations require a wsh policy')
        owned_index = self.owned_key_indexes[0]
        owned_key = self.keys[owned_index]
        owned_fingerprint = _fingerprint_int(owned_key.fingerprint)
        if owned_fingerprint != my_xfp:
            raise PolicyMismatchError('Registered policy belongs to another seed')

        owned_expressions = [key for key in iter_policy_keys(self.miniscript)
                             if key.index == owned_index]
        candidates = set()
        prefix = [owned_fingerprint] + list(owned_key.path)
        for public_key, path in subpaths.items():
            if len(path) != len(prefix) + 2 or list(path[:len(prefix)]) != prefix:
                continue
            child_branch, address_index = path[-2:]
            if child_branch >= 0x80000000 or address_index >= 0x80000000:
                continue
            for expression in owned_expressions:
                for branch in (0, 1):
                    if expression.branches[branch] == child_branch:
                        candidates.add((branch, address_index))

        matches = []
        for branch, address_index in candidates:
            try:
                derived, expected_paths, expected_key_indexes = self._derive_with_paths(
                    branch, address_index, chain)
                if derived.script_pubkey != bytes(utxo_script_pubkey):
                    continue
                if witness_script is not None and \
                        derived.witness_script != bytes(witness_script):
                    continue
                if set(expected_paths) != set(subpaths):
                    continue
                if any(expected_paths[key] != list(subpaths[key]) for key in expected_paths):
                    continue
                matches.append((derived, expected_paths, expected_key_indexes))
            except (WalletPolicyError, ValueError, TypeError):
                continue

        if not matches:
            raise PolicyMismatchError('PSBT scripts and derivations do not match the registered policy')
        if len(matches) != 1:
            raise PolicyMismatchError('PSBT derivation matches the policy ambiguously')
        return matches[0]

    def make_spend_plan(self, input_index, subpaths, utxo_script_pubkey,
                        witness_script, chain, my_xfp, sighash_type):
        if self.context != 'wsh':
            raise PolicyMismatchError('P2WSH spend matching requires a wsh policy')
        if sighash_type != 1:
            raise PolicyMismatchError('P2WSH wallet policies require SIGHASH_ALL')
        derived, expected_paths, expected_key_indexes = self.match_derivations(
            subpaths, utxo_script_pubkey, witness_script, chain, my_xfp)
        owned_index = self.owned_key_indexes[0]
        owned_pubkeys = [public_key for public_key, key_index in expected_key_indexes.items()
                         if key_index == owned_index]
        if not owned_pubkeys:
            raise PolicyMismatchError('Policy did not derive a Passport signing key')
        owned_signing_keys = tuple(
            (expected_paths[public_key], public_key) for public_key in owned_pubkeys)
        owned_path, owned_pubkey = owned_signing_keys[0]
        from miniscript import policy_timelocks
        from spend_plan import SpendPlan
        return SpendPlan(
            self.policy_id, input_index, derived.branch, derived.index, 'p2wsh',
            owned_path, owned_pubkey, sighash_type,
            script_pubkey=derived.script_pubkey,
            witness_script=derived.witness_script,
            timelocks=policy_timelocks(self.miniscript),
            owned_signing_keys=owned_signing_keys)

    def derive(self, branch, index, chain, key_resolver=None):
        if getattr(chain, 'ctype', None) != self.network:
            raise PolicyMismatchError('Policy network does not match the active network')
        resolver = key_resolver or self._resolver(chain)
        witness_script = compile_miniscript(
            self.miniscript, resolver, branch, index, 'wsh')
        digest = _sha256(witness_script)
        script_pubkey = b'\x00\x20' + digest
        try:
            from public_constants import AF_P2WSH
            address = chain.p2sh_address(AF_P2WSH, witness_script)
        except ImportError:  # Host tests may use a minimal chain stub.
            address = None
        return DerivedPolicyOutput(self.policy_id, branch, index, witness_script,
                                   script_pubkey, address)

    def match_scripts(self, branch, index, chain, utxo_script_pubkey,
                      witness_script=None, key_resolver=None):
        derived = self.derive(branch, index, chain, key_resolver)
        if bytes(utxo_script_pubkey) != derived.script_pubkey:
            raise PolicyMismatchError('UTXO script does not match the registered policy')
        if self.context == 'wsh' and witness_script is not None and \
                bytes(witness_script) != derived.witness_script:
            raise PolicyMismatchError('PSBT witness script does not match the registered policy')
        return derived


class WalletPolicyRegistry:
    """Validated storage facade; corrupt records are quarantined, never used."""

    def __init__(self, settings=None):
        if settings is None:
            from common import settings as global_settings
            settings = global_settings
        self.settings = settings
        self.invalid_records = []

    def _records(self):
        records = self.settings.get(POLICY_STORAGE_KEY, [])
        return records if isinstance(records, list) else []

    def iter_policies(self, fingerprint=None):
        self.invalid_records = []
        for record in self._records():
            try:
                policy = MiniscriptPolicy.deserialize(record)
                if fingerprint is not None:
                    owned = policy.keys[policy.owned_key_indexes[0]].fingerprint
                    if owned.lower() != fingerprint.lower():
                        continue
                yield policy
            except (WalletPolicyError, TypeError, KeyError, ValueError) as exc:
                self.invalid_records.append((record, str(exc)))

    def iter_all(self, fingerprint=None, include_legacy=True):
        for policy in self.iter_policies(fingerprint):
            yield policy
        if include_legacy:
            from multisig_wallet import MultisigWallet
            from policy_multisig import StandardMultisigPolicy
            if fingerprint is None:
                wallets = MultisigWallet.iter_wallets()
            else:
                from utils import str2xfp
                wallets = MultisigWallet.get_by_xfp(str2xfp(fingerprint))
            for wallet in wallets:
                yield StandardMultisigPolicy(wallet)

    def get(self, policy_id):
        for policy in self.iter_policies():
            if policy.policy_id == policy_id:
                return policy
        return None

    def _preflight(self, records):
        current = (self.settings.temporary_settings if getattr(self.settings, 'temporary_mode', False)
                   else self.settings.current)
        candidate = dict(current)
        candidate[POLICY_STORAGE_KEY] = records
        encoded_len = len(json.dumps(candidate))
        maximum = getattr(self.settings, 'max_json_len', 8192 - 32)
        if encoded_len > maximum - SETTINGS_HEADROOM:
            raise PolicyResourceError('Not enough settings space to store this policy safely')

    def save(self, policy):
        records = list(self._records())
        if any(record.get('id') == policy.policy_id for record in records if isinstance(record, dict)):
            raise PolicyParseError('This wallet policy is already registered')
        records.append(policy.serialize())
        self._preflight(records)
        self.settings.set(POLICY_STORAGE_KEY, records)

    def delete(self, policy_id):
        records = [record for record in self._records()
                   if not isinstance(record, dict) or record.get('id') != policy_id]
        self._preflight(records)
        self.settings.set(POLICY_STORAGE_KEY, records)

    def rename(self, policy_id, name):
        records = list(self._records())
        for position, record in enumerate(records):
            if isinstance(record, dict) and record.get('id') == policy_id:
                records[position] = MiniscriptPolicy.deserialize(record).rename(name).serialize()
                self._preflight(records)
                self.settings.set(POLICY_STORAGE_KEY, records)
                return
        raise PolicyParseError('Wallet policy was not found')

    def rename_key(self, policy_id, key_index, name):
        records = list(self._records())
        for position, record in enumerate(records):
            if isinstance(record, dict) and record.get('id') == policy_id:
                policy = MiniscriptPolicy.deserialize(record).name_key(key_index, name)
                records[position] = policy.serialize()
                self._preflight(records)
                self.settings.set(POLICY_STORAGE_KEY, records)
                return
        raise PolicyParseError('Wallet policy was not found')

    def rename_keys(self, policy_id, names):
        records = list(self._records())
        for position, record in enumerate(records):
            if isinstance(record, dict) and record.get('id') == policy_id:
                policy = MiniscriptPolicy.deserialize(record).name_keys(names)
                records[position] = policy.serialize()
                self._preflight(records)
                self.settings.set(POLICY_STORAGE_KEY, records)
                return
        raise PolicyParseError('Wallet policy was not found')
