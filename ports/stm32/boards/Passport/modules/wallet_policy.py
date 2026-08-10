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
                           PolicyResourceError, WalletPolicyError)


POLICY_FORMAT_VERSION = 1
POLICY_STORAGE_KEY = 'wallet_policies'
MAX_POLICY_NAME_LENGTH = 20
MAX_POLICY_RECORD_LENGTH = 3072
SETTINGS_HEADROOM = 768
BASE58_CHARS = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
MAX_TAPROOT_TREE_DEPTH = 4
MAX_TAPROOT_LEAVES = 8
TAPSCRIPT_LEAF_VERSION = 0xc0


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


def _valid_xonly_key(value):
    """Validate a BIP340 x-only key without importing firmware crypto modules."""
    if not isinstance(value, (bytes, bytearray)) or len(value) != 32:
        return False
    field = 0xfffffffffffffffffffffffffffffffffffffffffffffffffffffffefffffc2f
    x_value = int.from_bytes(value, 'big')
    if x_value >= field:
        return False
    square = (pow(x_value, 3, field) + 7) % field
    root = pow(square, (field + 1) // 4, field)
    return pow(root, 2, field) == square


def _tagged_hash(tag, message):
    tag_hash = _sha256(tag.encode('ascii'))
    return _sha256(tag_hash + tag_hash + message)


def _tapleaf_hash(script):
    return _tagged_hash('TapLeaf', bytes([TAPSCRIPT_LEAF_VERSION]) +
                        _compact_size(len(script)) + script)


def _taproot_tree_helper(script_tree):
    if isinstance(script_tree, tuple):
        leaf_version, script = script_tree
        leaf_hash = _tagged_hash(
            'TapLeaf', bytes([leaf_version]) + _compact_size(len(script)) + script)
        return [((leaf_version, script), b'')], leaf_hash
    left, left_hash = _taproot_tree_helper(script_tree[0])
    right, right_hash = _taproot_tree_helper(script_tree[1])
    leaves = [(leaf, path + right_hash) for leaf, path in left]
    leaves.extend((leaf, path + left_hash) for leaf, path in right)
    low, high = ((left_hash, right_hash) if left_hash < right_hash
                 else (right_hash, left_hash))
    return leaves, _tagged_hash('TapBranch', low + high)


def _host_tweak_internal_key(internal_key, merkle_root):
    """Small host fallback; firmware uses the optimized taproot module."""
    field = 0xfffffffffffffffffffffffffffffffffffffffffffffffffffffffefffffc2f
    order = 0xfffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141
    generator = (
        0x79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798,
        0x483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8)

    def add(left, right):
        if left is None:
            return right
        if right is None:
            return left
        x_left, y_left = left
        x_right, y_right = right
        if x_left == x_right:
            if (y_left + y_right) % field == 0:
                return None
            slope = (3 * x_left * x_left) * pow(2 * y_left, field - 2, field)
        else:
            slope = (y_right - y_left) * pow(x_right - x_left, field - 2, field)
        slope %= field
        x_result = (slope * slope - x_left - x_right) % field
        return x_result, (slope * (x_left - x_result) - y_left) % field

    def multiply(scalar, point):
        result = None
        while scalar:
            if scalar & 1:
                result = add(result, point)
            point = add(point, point)
            scalar >>= 1
        return result

    x_value = int.from_bytes(internal_key, 'big')
    square = (pow(x_value, 3, field) + 7) % field
    y_value = pow(square, (field + 1) // 4, field)
    if y_value & 1:
        y_value = field - y_value
    tweak = int.from_bytes(_tagged_hash('TapTweak', internal_key + merkle_root), 'big')
    if tweak >= order:
        raise PolicyMismatchError('Taproot tweak is outside the curve order')
    output = add((x_value, y_value), multiply(tweak, generator))
    if output is None:
        raise PolicyMismatchError('Taproot tweak produced the point at infinity')
    return output[1] & 1, output[0].to_bytes(32, 'big')


def _tweak_internal_key(internal_key, merkle_root):
    try:
        from taproot import tweak_internal_key
        return tweak_internal_key(internal_key, merkle_root)
    except ImportError:  # pragma: no cover - used by CPython host tests
        return _host_tweak_internal_key(internal_key, merkle_root)


def _split_descriptor_pair(text):
    """Split one descriptor-level comma, respecting Miniscript and tree nesting."""
    parens = 0
    braces = 0
    split_at = -1
    for position, char in enumerate(text):
        if char == '(':
            parens += 1
        elif char == ')':
            parens -= 1
        elif char == '{':
            braces += 1
        elif char == '}':
            braces -= 1
        elif char == ',' and parens == 0 and braces == 0:
            if split_at >= 0:
                raise PolicyParseError('Taproot descriptor has too many top-level arguments')
            split_at = position
        if parens < 0 or braces < 0:
            raise PolicyParseError('Taproot descriptor delimiters are unbalanced')
    if parens or braces or split_at < 0:
        raise PolicyParseError('Taproot descriptor requires an internal key and script tree')
    return text[:split_at], text[split_at + 1:]


def _parse_taproot_tree(text, depth=0, counter=None):
    if counter is None:
        counter = [0]
    if depth > MAX_TAPROOT_TREE_DEPTH:
        raise PolicyResourceError(
            'Taproot tree depth exceeds {}'.format(MAX_TAPROOT_TREE_DEPTH))
    if text.startswith('{'):
        if not text.endswith('}'):
            raise PolicyParseError('Taproot tree branch is missing a closing brace')
        left, right = _split_descriptor_pair(text[1:-1])
        if not left or not right:
            raise PolicyParseError('Taproot tree branch contains an empty child')
        return [_parse_taproot_tree(left, depth + 1, counter),
                _parse_taproot_tree(right, depth + 1, counter)]
    if not text or '{' in text or '}' in text:
        raise PolicyParseError('Taproot tree leaf is malformed')
    counter[0] += 1
    if counter[0] > MAX_TAPROOT_LEAVES:
        raise PolicyResourceError(
            'Taproot tree contains more than {} leaves'.format(MAX_TAPROOT_LEAVES))
    node = Parser(text).parse()
    validate(node, 'tr')
    return node


def _walk_taproot_leaves(tree, depth=0):
    if isinstance(tree, list):
        for leaf in _walk_taproot_leaves(tree[0], depth + 1):
            yield leaf
        for leaf in _walk_taproot_leaves(tree[1], depth + 1):
            yield leaf
    else:
        yield tree, depth


class TapLeafInfo:
    __slots__ = ('script', 'leaf_hash', 'control_block', 'key_indexes', 'depth')

    def __init__(self, script, leaf_hash, control_block, key_indexes, depth):
        self.script = script
        self.leaf_hash = leaf_hash
        self.control_block = control_block
        self.key_indexes = tuple(key_indexes)
        self.depth = depth


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
    if not ((body.startswith('wsh(') or body.startswith('tr(')) and body.endswith(')')):
        raise PolicyParseError('Imports require a top-level wsh or tr descriptor')
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
                 'redeem_script', 'script_pubkey', 'address', 'internal_key',
                 'merkle_root', 'tap_leaves', 'tap_tree')

    def __init__(self, policy_id, branch, index, witness_script,
                 script_pubkey, address, redeem_script=None, internal_key=None,
                 merkle_root=None, tap_leaves=(), tap_tree=None):
        self.policy_id = policy_id
        self.branch = branch
        self.index = index
        self.witness_script = witness_script
        self.redeem_script = redeem_script
        self.script_pubkey = script_pubkey
        self.address = address
        self.internal_key = internal_key
        self.merkle_root = merkle_root
        self.tap_leaves = tuple(tap_leaves)
        self.tap_tree = tap_tree


class MiniscriptPolicy:
    __slots__ = ('name', 'network', 'template', 'keys', 'owned_key_indexes',
                 'miniscript', 'script_tree', 'internal_key', 'context',
                 'policy_id')

    def __init__(self, name, network, template, keys, owned_key_indexes):
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

        script_tree = None
        internal_key = None
        if template.startswith('wsh(') and template.endswith(')'):
            context = 'wsh'
            miniscript = Parser(template[4:-1]).parse()
            validate(miniscript, context)
            key_expressions = list(iter_policy_keys(miniscript))
        elif template.startswith('tr(') and template.endswith(')'):
            context = 'tr'
            internal_text, tree_text = _split_descriptor_pair(template[3:-1])
            if len(internal_text) == 64 and all(
                    char in '0123456789abcdefABCDEF' for char in internal_text):
                internal_key = unhexlify(internal_text)
                if not _valid_xonly_key(internal_key):
                    raise PolicyParseError('Taproot internal key is not a curve point')
            else:
                internal_node = Parser('pk_k(' + internal_text + ')').parse()
                internal_key = internal_node.value
            script_tree = _parse_taproot_tree(tree_text)
            leaves = [leaf for leaf, _ in _walk_taproot_leaves(script_tree)]
            miniscript = leaves[0]
            key_expressions = []
            if not isinstance(internal_key, bytes):
                key_expressions.append(internal_key)
            for leaf in leaves:
                key_expressions.extend(iter_policy_keys(leaf))

            # This first script-path profile intentionally rejects repeated key
            # expressions and overlapping derivation branches across leaves.
            seen = set()
            branches_by_key = {}
            for expression in key_expressions:
                identity = expression.identity()
                if identity in seen:
                    raise PolicyParseError('A key expression is repeated in the Taproot policy')
                seen.add(identity)
                branch_set = set(expression.branches)
                previous = branches_by_key.get(expression.index, set())
                if previous.intersection(branch_set):
                    raise PolicyParseError(
                        'Taproot derivation branches overlap for key @{}'.format(expression.index))
                branches_by_key[expression.index] = previous.union(branch_set)
        else:
            raise PolicyParseError('Policies must use a top-level wsh or tr descriptor')

        if not 1 <= len(keys) <= MAX_KEYS:
            raise PolicyResourceError('Policy must contain between 1 and {} keys'.format(MAX_KEYS))
        parsed_keys = tuple(key if isinstance(key, KeyInfo) else KeyInfo.parse(key) for key in keys)
        canonical_keys = [key.canonical() for key in parsed_keys]
        if len(set(canonical_keys)) != len(canonical_keys):
            raise PolicyParseError('Policy key information entries must be distinct')

        indexes = [key.index for key in key_expressions]
        if context == 'tr' and len(indexes) != len(set(indexes)):
            raise PolicyParseError(
                'Each key entry may appear only once in the Taproot policy profile')
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
        if indexes.count(owned[0]) != 1:
            raise PolicyParseError('Policies require exactly one Passport signing key per input')
        if context == 'tr' and not isinstance(internal_key, bytes) and \
                internal_key.index == owned[0]:
            raise PolicyParseError(
                'Passport-owned Taproot keys must be in a script leaf, not the internal key')

        self.name = name
        self.network = network
        self.template = template
        self.keys = parsed_keys
        self.owned_key_indexes = owned
        self.miniscript = miniscript
        self.script_tree = script_tree
        self.internal_key = internal_key
        self.context = context
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
                     record.get('k', ()), record.get('o', ()))
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
        return {
            'v': POLICY_FORMAT_VERSION,
            'id': self.policy_id,
            'n': self.name,
            'net': self.network,
            't': self.template,
            'k': [key.canonical() for key in self.keys],
            'o': list(self.owned_key_indexes),
        }

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
        lines = ['TECHNICAL DETAILS',
                 'Full Descriptor\n' + self.full_descriptor()]
        for index, key in enumerate(self.keys):
            role = 'This Passport' if index in self.owned_key_indexes else 'External key'
            lines.append('Key {} - {}\nFingerprint {}\nPath {}\n{}'.format(
                index + 1, role, key.fingerprint.upper(),
                self._format_origin_path(key.path), key.xpub))
        lines.append('Internal Policy ID\n' + self.policy_id)
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

    def rename(self, name):
        return MiniscriptPolicy(name, self.network, self.template, self.keys,
                                self.owned_key_indexes)

    def _leaves(self):
        if self.context == 'wsh':
            yield self.miniscript
        else:
            for leaf, _ in _walk_taproot_leaves(self.script_tree):
                yield leaf

    def _key_expressions(self):
        if self.context == 'tr' and not isinstance(self.internal_key, bytes):
            yield self.internal_key
        for leaf in self._leaves():
            for expression in iter_policy_keys(leaf):
                yield expression

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
            if self.context == 'tr':
                public_key = public_key[1:]
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
                if derived.witness_script != bytes(witness_script):
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

    def _derive_taproot_with_paths(self, branch, index, chain):
        derived, expected_paths, expected_key_indexes = self._derive_with_paths(
            branch, index, chain)
        expected_hashes = {}
        for public_key, key_index in expected_key_indexes.items():
            hashes = []
            for leaf in derived.tap_leaves:
                if key_index in leaf.key_indexes:
                    hashes.append(leaf.leaf_hash)
            expected_hashes[public_key] = tuple(hashes)
        return derived, expected_paths, expected_key_indexes, expected_hashes

    @staticmethod
    def _tap_hashes_equal(provided, expected):
        if len(provided) != len(expected):
            return False
        if len(set(provided)) != len(provided):
            return False
        return set(provided) == set(expected)

    def match_taproot_derivations(self, tap_subpaths, utxo_script_pubkey,
                                  tap_leaf_scripts, tap_internal_key,
                                  tap_merkle_root, chain, my_xfp):
        """Resolve and exactly bind a BIP371 script-path input to this policy."""
        if self.context != 'tr':
            raise PolicyMismatchError('Taproot derivations require a tr policy')
        owned_index = self.owned_key_indexes[0]
        owned_key = self.keys[owned_index]
        owned_fingerprint = _fingerprint_int(owned_key.fingerprint)
        if owned_fingerprint != my_xfp:
            raise PolicyMismatchError('Registered policy belongs to another seed')

        owned_expressions = [expression for expression in self._key_expressions()
                             if expression.index == owned_index]
        candidates = set()
        prefix = [owned_fingerprint] + list(owned_key.path)
        for _, (path, _) in tap_subpaths.items():
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
                derived, expected_paths, expected_indexes, expected_hashes = \
                    self._derive_taproot_with_paths(branch, address_index, chain)
                if derived.script_pubkey != bytes(utxo_script_pubkey):
                    continue
                if set(expected_paths) != set(tap_subpaths):
                    continue
                metadata_matches = True
                for public_key, expected_path in expected_paths.items():
                    provided_path, provided_hashes = tap_subpaths[public_key]
                    if list(provided_path) != expected_path or not self._tap_hashes_equal(
                            provided_hashes, expected_hashes[public_key]):
                        metadata_matches = False
                        break
                if not metadata_matches:
                    continue
                if tap_internal_key is not None and \
                        bytes(tap_internal_key) != derived.internal_key:
                    continue
                if tap_merkle_root is not None and \
                        bytes(tap_merkle_root) != derived.merkle_root:
                    continue

                owned_pubkeys = [public_key for public_key, key_index in expected_indexes.items()
                                 if key_index == owned_index]
                if len(owned_pubkeys) != 1:
                    continue
                owned_pubkey = owned_pubkeys[0]
                owned_leaves = [leaf for leaf in derived.tap_leaves
                                if owned_index in leaf.key_indexes]
                if len(owned_leaves) != 1:
                    continue
                leaf = owned_leaves[0]
                expected_leaf_value = leaf.script + bytes([TAPSCRIPT_LEAF_VERSION])
                if len(tap_leaf_scripts) != 1 or \
                        tap_leaf_scripts.get(leaf.control_block) != expected_leaf_value:
                    continue
                matches.append((derived, expected_paths, expected_indexes,
                                expected_hashes, owned_pubkey, leaf))
            except (WalletPolicyError, ValueError, TypeError):
                continue

        if not matches:
            raise PolicyMismatchError(
                'Taproot scripts, control block, and derivations do not match the registered policy')
        if len(matches) != 1:
            raise PolicyMismatchError('Taproot derivation matches the policy ambiguously')
        return matches[0]

    def make_taproot_spend_plan(self, input_index, tap_subpaths,
                                utxo_script_pubkey, tap_leaf_scripts,
                                tap_internal_key, tap_merkle_root, chain,
                                my_xfp, sighash_type):
        if sighash_type != 0:
            raise PolicyMismatchError(
                'Taproot wallet policies require SIGHASH_DEFAULT')
        result = self.match_taproot_derivations(
            tap_subpaths, utxo_script_pubkey, tap_leaf_scripts,
            tap_internal_key, tap_merkle_root, chain, my_xfp)
        derived, expected_paths, _, _, owned_pubkey, leaf = result
        from miniscript import policy_timelocks
        from spend_plan import SpendPlan
        locks = []
        for miniscript in self._leaves():
            locks.extend(policy_timelocks(miniscript))
        return SpendPlan(
            self.policy_id, input_index, derived.branch, derived.index,
            'tapscript', expected_paths[owned_pubkey], owned_pubkey,
            sighash_type, script_pubkey=derived.script_pubkey,
            tapleaf_script=leaf.script, tapleaf_hash=leaf.leaf_hash,
            control_block=leaf.control_block, internal_key=derived.internal_key,
            merkle_root=derived.merkle_root, timelocks=locks)

    def match_taproot_change(self, tap_subpaths, script_pubkey,
                             tap_internal_key, tap_tree, chain, my_xfp):
        """Classify change only when every BIP371 output field is exact."""
        if self.context != 'tr':
            raise PolicyMismatchError('Taproot change requires a tr policy')
        owned_key = self.keys[self.owned_key_indexes[0]]
        owned_fingerprint = _fingerprint_int(owned_key.fingerprint)
        if owned_fingerprint != my_xfp:
            raise PolicyMismatchError('Registered policy belongs to another seed')
        prefix = [owned_fingerprint] + list(owned_key.path)
        candidates = set()
        for _, (path, _) in tap_subpaths.items():
            if len(path) == len(prefix) + 2 and list(path[:len(prefix)]) == prefix:
                for expression in self._key_expressions():
                    if expression.index != self.owned_key_indexes[0]:
                        continue
                    for branch in (0, 1):
                        if expression.branches[branch] == path[-2]:
                            candidates.add((branch, path[-1]))
        matches = []
        for branch, address_index in candidates:
            try:
                derived, expected_paths, _, expected_hashes = \
                    self._derive_taproot_with_paths(branch, address_index, chain)
                if derived.script_pubkey != bytes(script_pubkey):
                    continue
                if tap_internal_key is None or bytes(tap_internal_key) != derived.internal_key:
                    continue
                if tap_tree is None or bytes(tap_tree) != derived.tap_tree:
                    continue
                if set(expected_paths) != set(tap_subpaths):
                    continue
                if any(list(tap_subpaths[key][0]) != expected_paths[key] or
                       not self._tap_hashes_equal(tap_subpaths[key][1], expected_hashes[key])
                       for key in expected_paths):
                    continue
                matches.append(derived)
            except (WalletPolicyError, ValueError, TypeError):
                continue
        if len(matches) != 1:
            raise PolicyMismatchError(
                'Taproot change output does not exactly match the registered policy')
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
        if len(owned_pubkeys) != 1:
            raise PolicyMismatchError('Policy must derive exactly one Passport signing key')
        owned_pubkey = owned_pubkeys[0]
        from miniscript import policy_timelocks
        from spend_plan import SpendPlan
        return SpendPlan(
            self.policy_id, input_index, derived.branch, derived.index, 'p2wsh',
            expected_paths[owned_pubkey], owned_pubkey, sighash_type,
            script_pubkey=derived.script_pubkey,
            witness_script=derived.witness_script,
            timelocks=policy_timelocks(self.miniscript))

    def _compile_tap_tree(self, tree, resolver, branch, index, depth, records):
        if isinstance(tree, list):
            return [self._compile_tap_tree(tree[0], resolver, branch, index,
                                           depth + 1, records),
                    self._compile_tap_tree(tree[1], resolver, branch, index,
                                           depth + 1, records)]
        script = compile_miniscript(tree, resolver, branch, index, 'tr')
        records.append((tree, script, depth))
        return TAPSCRIPT_LEAF_VERSION, script

    def derive(self, branch, index, chain, key_resolver=None):
        if getattr(chain, 'ctype', None) != self.network:
            raise PolicyMismatchError('Policy network does not match the active network')
        resolver = key_resolver or self._resolver(chain)
        if self.context == 'wsh':
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

        if isinstance(self.internal_key, bytes):
            internal_key = self.internal_key
        else:
            internal_key = resolver(self.internal_key.index,
                                    self.internal_key.branches[branch], index)
        if not _valid_xonly_key(internal_key):
            raise PolicyMismatchError('Derived Taproot internal key is invalid')

        records = []
        compiled_tree = self._compile_tap_tree(
            self.script_tree, resolver, branch, index, 0, records)
        tree_info, merkle_root = _taproot_tree_helper(compiled_tree)
        parity, output_key = _tweak_internal_key(internal_key, merkle_root)
        script_pubkey = b'\x51\x20' + output_key
        leaves = []
        tree_encoding = b''
        for position, ((leaf_version, script), merkle_path) in enumerate(tree_info):
            node, recorded_script, depth = records[position]
            if leaf_version != TAPSCRIPT_LEAF_VERSION or script != recorded_script:
                raise PolicyMismatchError('Taproot leaf traversal changed during derivation')
            control_block = bytes([leaf_version | parity]) + internal_key + merkle_path
            key_indexes = [expression.index for expression in iter_policy_keys(node)]
            leaves.append(TapLeafInfo(
                script, _tapleaf_hash(script), control_block, key_indexes, depth))
            tree_encoding += bytes([depth, leaf_version])
            tree_encoding += _compact_size(len(script)) + script
        try:
            address = chain.render_address(script_pubkey)
        except (AttributeError, ImportError):
            address = None
        return DerivedPolicyOutput(
            self.policy_id, branch, index, None, script_pubkey, address,
            internal_key=internal_key, merkle_root=merkle_root,
            tap_leaves=leaves, tap_tree=tree_encoding)

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
