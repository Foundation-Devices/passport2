# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Bounded Miniscript parsing, analysis, and script compilation.

This module deliberately has no UI, settings, or secret-key dependencies.  It
implements the BIP379 grammar and a conservative registered-policy profile.
P2WSH and Tapscript use distinct validation contexts so fragments cannot cross
their consensus environments accidentally.
"""

try:
    from ubinascii import unhexlify
except ImportError:  # pragma: no cover - CPython host tests
    from binascii import unhexlify

from policy_errors import (PolicyParseError, PolicyResourceError,
                           PolicyTypeError, UnsupportedPolicyError)


MAX_TEMPLATE_LENGTH = 512
MAX_PARSE_DEPTH = 16
MAX_AST_NODES = 128
MAX_THRESH_ITEMS = 24
MAX_KEYS = 15
MAX_P2WSH_SCRIPT_SIZE = 3600
MAX_P2WSH_OPS = 201


# Script opcodes used by BIP379.  Keeping them local makes the pure policy
# module importable under both MicroPython and CPython.
OP_0 = 0x00
OP_1 = 0x51
OP_16 = 0x60
OP_IF = 0x63
OP_NOTIF = 0x64
OP_ELSE = 0x67
OP_ENDIF = 0x68
OP_VERIFY = 0x69
OP_TOALTSTACK = 0x6b
OP_FROMALTSTACK = 0x6c
OP_IFDUP = 0x73
OP_DUP = 0x76
OP_SWAP = 0x7c
OP_SIZE = 0x82
OP_EQUAL = 0x87
OP_EQUALVERIFY = 0x88
OP_0NOTEQUAL = 0x92
OP_ADD = 0x93
OP_BOOLAND = 0x9a
OP_BOOLOR = 0x9b
OP_NUMEQUAL = 0x9c
OP_NUMEQUALVERIFY = 0x9d
OP_RIPEMD160 = 0xa6
OP_SHA256 = 0xa8
OP_HASH160 = 0xa9
OP_HASH256 = 0xaa
OP_CHECKSIG = 0xac
OP_CHECKSIGVERIFY = 0xad
OP_CHECKMULTISIG = 0xae
OP_CHECKMULTISIGVERIFY = 0xaf
OP_CHECKLOCKTIMEVERIFY = 0xb1
OP_CHECKSEQUENCEVERIFY = 0xb2
OP_CHECKSIGADD = 0xba


def _is_ascii_digit(ch):
    return len(ch) == 1 and '0' <= ch <= '9'


def _is_ascii_alpha(ch):
    return len(ch) == 1 and ('a' <= ch <= 'z' or 'A' <= ch <= 'Z')


def _is_ascii_alnum(ch):
    return _is_ascii_alpha(ch) or _is_ascii_digit(ch)


class PolicyKey:
    __slots__ = ('index', 'branches')

    def __init__(self, index, branches=(0, 1)):
        self.index = index
        self.branches = branches

    def identity(self):
        return self.index, self.branches[0], self.branches[1]

    def __repr__(self):
        if self.branches == (0, 1):
            return '@{}/**'.format(self.index)
        return '@{}/<{};{}>/*'.format(self.index, self.branches[0], self.branches[1])


class Node:
    __slots__ = ('kind', 'args', 'value')

    def __init__(self, kind, args=(), value=None):
        self.kind = kind
        self.args = args
        self.value = value

    def __repr__(self):
        return 'Node({!r}, {!r}, {!r})'.format(self.kind, self.args, self.value)


class TypeInfo:
    __slots__ = ('basic', 'z', 'o', 'n', 'd', 'u', 's', 'f', 'e', 'locks')

    def __init__(self, basic, z=False, o=False, n=False, d=False, u=False,
                 s=False, f=False, e=False, locks=0):
        self.basic = basic
        self.z = z
        self.o = o
        self.n = n
        self.d = d
        self.u = u
        self.s = s
        self.f = f
        self.e = e
        self.locks = locks

    def is_type(self, basic, *properties):
        if self.basic != basic:
            return False
        return all(getattr(self, prop) for prop in properties)


class Parser:
    _WRAPPERS = 'asctdvjnlu'

    def __init__(self, text, max_depth=MAX_PARSE_DEPTH, max_nodes=MAX_AST_NODES,
                 max_keys=MAX_KEYS):
        if not isinstance(text, str):
            raise PolicyParseError('Policy template must be text')
        if len(text) > MAX_TEMPLATE_LENGTH:
            raise PolicyResourceError('Policy template exceeds {} characters'.format(MAX_TEMPLATE_LENGTH))
        try:
            text.encode('ascii')
        except UnicodeError:
            raise PolicyParseError('Policy template must contain ASCII only')
        if '\x00' in text:
            raise PolicyParseError('Policy template contains a NUL character')
        self.text = text
        self.length = len(text)
        self.pos = 0
        self.max_depth = max_depth
        self.max_nodes = max_nodes
        self.max_keys = max_keys
        self.node_count = 0

    def _error(self, message):
        raise PolicyParseError(message, self.pos)

    def _node(self, kind, args=(), value=None):
        self.node_count += 1
        if self.node_count > self.max_nodes:
            raise PolicyResourceError('Policy contains more than {} expressions'.format(self.max_nodes))
        return Node(kind, args, value)

    def _peek(self):
        if self.pos >= self.length:
            return ''
        return self.text[self.pos]

    def _take(self, expected=None):
        if self.pos >= self.length:
            self._error('Unexpected end of policy')
        ch = self.text[self.pos]
        if expected is not None and ch != expected:
            self._error("Expected '{}'".format(expected))
        self.pos += 1
        return ch

    def _identifier(self):
        start = self.pos
        while _is_ascii_alnum(self._peek()) or self._peek() == '_':
            self.pos += 1
        if self.pos == start:
            self._error('Expected expression name')
        return self.text[start:self.pos]

    def _number(self):
        start = self.pos
        while _is_ascii_digit(self._peek()):
            self.pos += 1
        if self.pos == start:
            self._error('Expected decimal number')
        token = self.text[start:self.pos]
        if len(token) > 1 and token[0] == '0':
            self._error('Decimal numbers must not have leading zeroes')
        if len(token) > 10:
            raise PolicyResourceError('Decimal number is too large')
        value = int(token)
        if value > 0xffffffff:
            raise PolicyResourceError('Decimal number is too large')
        return value

    def _hex(self, expected_bytes):
        start = self.pos
        expected_chars = expected_bytes * 2
        end = start + expected_chars
        if end > self.length:
            self._error('Hash value is truncated')
        token = self.text[start:end]
        for ch in token:
            if ch not in '0123456789abcdefABCDEF':
                self._error('Hash value is not hexadecimal')
        self.pos = end
        return token.lower()

    def _key(self):
        self._take('@')
        index = self._number()
        if index >= self.max_keys:
            raise PolicyResourceError('Key index exceeds {}'.format(self.max_keys - 1))
        self._take('/')
        if self.text[self.pos:self.pos + 2] == '**':
            self.pos += 2
            return PolicyKey(index)
        self._take('<')
        first = self._number()
        self._take(';')
        second = self._number()
        self._take('>')
        self._take('/')
        self._take('*')
        if first == second:
            self._error('Receive and change branches must be different')
        if first >= 0x80000000 or second >= 0x80000000:
            raise PolicyResourceError('Policy branches must be unhardened')
        return PolicyKey(index, (first, second))

    def parse(self):
        node = self._expr(0)
        if self.pos != self.length:
            self._error('Unexpected trailing characters')
        return node

    def _expr(self, depth):
        if depth > self.max_depth:
            raise PolicyResourceError('Policy nesting exceeds {}'.format(self.max_depth))

        # Wrappers can be combined before a single colon, for example sln:X.
        start = self.pos
        while _is_ascii_alpha(self._peek()):
            self.pos += 1
        if self._peek() == ':':
            wrappers = self.text[start:self.pos]
            if not wrappers or any(ch not in self._WRAPPERS for ch in wrappers):
                self._error('Unknown Miniscript wrapper')
            self.pos += 1
            child = self._expr(depth + 1)
            for wrapper in reversed(wrappers):
                child = self._apply_wrapper(wrapper, child)
            return child
        self.pos = start

        if self._peek() in ('0', '1'):
            ch = self._take()
            if _is_ascii_digit(self._peek()) or self._peek() == '(':
                self._error('Invalid constant')
            return self._node(ch)

        name = self._identifier()
        self._take('(')

        if name in ('pk', 'pkh', 'pk_k', 'pk_h'):
            key = self._key()
            self._take(')')
            base = self._node('pk_k' if name in ('pk', 'pk_k') else 'pk_h', value=key)
            if name in ('pk', 'pkh'):
                return self._node('c', (base,))
            return base

        if name in ('older', 'after'):
            value = self._number()
            self._take(')')
            return self._node(name, value=value)

        if name in ('sha256', 'hash256'):
            value = self._hex(32)
            self._take(')')
            return self._node(name, value=value)

        if name in ('ripemd160', 'hash160'):
            value = self._hex(20)
            self._take(')')
            return self._node(name, value=value)

        if name in ('and_v', 'and_b', 'and_n', 'or_b', 'or_c', 'or_d', 'or_i'):
            left = self._expr(depth + 1)
            self._take(',')
            right = self._expr(depth + 1)
            self._take(')')
            if name == 'and_n':
                return self._node('andor', (left, right, self._node('0')))
            return self._node(name, (left, right))

        if name == 'andor':
            first = self._expr(depth + 1)
            self._take(',')
            second = self._expr(depth + 1)
            self._take(',')
            third = self._expr(depth + 1)
            self._take(')')
            return self._node(name, (first, second, third))

        if name == 'thresh':
            threshold = self._number()
            children = []
            while self._peek() == ',':
                self.pos += 1
                if len(children) >= MAX_THRESH_ITEMS:
                    raise PolicyResourceError('Threshold contains too many expressions')
                children.append(self._expr(depth + 1))
            self._take(')')
            return self._node(name, tuple(children), threshold)

        if name in ('multi', 'multi_a'):
            threshold = self._number()
            keys = []
            while self._peek() == ',':
                self.pos += 1
                key_limit = 20 if name == 'multi' else MAX_THRESH_ITEMS
                if len(keys) >= key_limit:
                    raise PolicyResourceError('{} contains too many keys'.format(name))
                keys.append(self._key())
            self._take(')')
            return self._node(name, tuple(keys), threshold)

        self._error("Unknown Miniscript fragment '{}'".format(name))

    def _apply_wrapper(self, wrapper, child):
        if wrapper == 't':
            return self._node('and_v', (child, self._node('1')))
        if wrapper == 'l':
            return self._node('or_i', (self._node('0'), child))
        if wrapper == 'u':
            return self._node('or_i', (child, self._node('0')))
        return self._node(wrapper, (child,))


def _require(condition, message):
    if not condition:
        raise PolicyTypeError(message)


def analyze(node, context='wsh'):
    """Return BIP379 correctness/malleability properties for an AST."""
    kind = node.kind
    args = node.args

    if kind == '0':
        return TypeInfo('B', z=True, u=True, d=True, s=True, e=True)
    if kind == '1':
        return TypeInfo('B', z=True, u=True, f=True)
    if kind == 'pk_k':
        return TypeInfo('K', o=True, n=True, d=True, u=True, s=True, e=True)
    if kind == 'pk_h':
        _require(context == 'wsh', 'pk_h is only valid in P2WSH')
        return TypeInfo('K', n=True, d=True, u=True, s=True, e=True)
    if kind in ('older', 'after'):
        _require(1 <= node.value < 0x80000000, '{} value is outside BIP379 range'.format(kind))
        if kind == 'older':
            # BIP68 only assigns the low 16 bits and the type flag. Accepting
            # reserved bits would make the number shown in a descriptor differ
            # from the relative delay actually enforced by consensus.
            allowed = 0xffff | (1 << 22)
            _require(not (node.value & ~allowed),
                     'older exceeds the BIP68 relative timelock limit or uses reserved bits')
            _require(node.value & 0xffff,
                     'older value must encode a non-zero relative delay')
        if kind == 'after':
            lock = 1 if node.value < 500000000 else 2
        else:
            lock = 4 if not (node.value & (1 << 22)) else 8
        return TypeInfo('B', z=True, f=True, locks=lock)
    if kind in ('sha256', 'hash256', 'ripemd160', 'hash160'):
        return TypeInfo('B', o=True, n=True, d=True, u=True)
    if kind in ('multi', 'multi_a'):
        count = len(args)
        _require(1 <= node.value <= count, '{} threshold is invalid'.format(kind))
        if kind == 'multi':
            _require(context == 'wsh', 'multi is only valid in P2WSH')
            _require(count <= 20, 'P2WSH multi is limited to 20 keys')
            return TypeInfo('B', n=True, d=True, u=True, s=True, e=True)
        _require(context == 'tr', 'multi_a is only valid in Tapscript')
        return TypeInfo('B', d=True, u=True, s=True, e=True)

    children = [analyze(child, context) for child in args]
    locks = 0
    for child in children:
        locks |= child.locks

    if kind == 'andor':
        x, y, zed = children
        _require(x.is_type('B', 'd', 'u'), 'andor first argument must be Bdu')
        _require(y.basic in ('B', 'K', 'V') and y.basic == zed.basic,
                 'andor branches must have the same B, K, or V type')
        _require(x.e and (x.s or y.s or zed.s), 'andor is malleable')
        return TypeInfo(y.basic,
                        z=x.z and y.z and zed.z,
                        o=(x.z and y.o and zed.o) or (x.o and y.z and zed.z),
                        u=y.u and zed.u, d=zed.d,
                        s=zed.s and (x.s or y.s),
                        f=zed.f and (x.s or y.f),
                        e=zed.e and (x.s or y.f), locks=locks)

    if kind == 'and_v':
        x, y = children
        _require(x.basic == 'V' and y.basic in ('B', 'K', 'V'),
                 'and_v requires V followed by B, K, or V')
        return TypeInfo(y.basic, z=x.z and y.z,
                        o=(x.z and y.o) or (y.z and x.o),
                        n=x.n or (x.z and y.n), u=y.u,
                        s=x.s or y.s, f=x.s or y.f, locks=locks)

    if kind == 'and_b':
        x, y = children
        _require(x.basic == 'B' and y.basic == 'W', 'and_b requires B and W')
        return TypeInfo('B', z=x.z and y.z,
                        o=(x.z and y.o) or (y.z and x.o),
                        n=x.n or (x.z and y.n), d=x.d and y.d, u=True,
                        s=x.s or y.s,
                        f=(x.f and y.f) or (x.s and x.f) or (y.s and y.f),
                        e=x.e and y.e and x.s and y.s, locks=locks)

    if kind == 'or_b':
        x, zed = children
        _require(x.is_type('B', 'd') and zed.is_type('W', 'd'),
                 'or_b requires Bd and Wd')
        _require(x.e and zed.e and (x.s or zed.s), 'or_b is malleable')
        return TypeInfo('B', z=x.z and zed.z,
                        o=(x.z and zed.o) or (zed.z and x.o),
                        d=True, u=True, s=x.s and zed.s, e=True, locks=locks)

    if kind == 'or_c':
        x, zed = children
        _require(x.is_type('B', 'd', 'u') and zed.basic == 'V',
                 'or_c requires Bdu and V')
        _require(x.e and (x.s or zed.s), 'or_c is malleable')
        return TypeInfo('V', z=x.z and zed.z, o=x.o and zed.z,
                        s=x.s and zed.s, f=True, locks=locks)

    if kind == 'or_d':
        x, zed = children
        _require(x.is_type('B', 'd', 'u') and zed.basic == 'B',
                 'or_d requires Bdu and B')
        _require(x.e and (x.s or zed.s), 'or_d is malleable')
        return TypeInfo('B', z=x.z and zed.z, o=x.o and zed.z,
                        d=zed.d, u=zed.u, s=x.s and zed.s,
                        f=zed.f, e=zed.e, locks=locks)

    if kind == 'or_i':
        x, zed = children
        _require(x.basic in ('B', 'K', 'V') and x.basic == zed.basic,
                 'or_i branches must have the same B, K, or V type')
        _require(x.s or zed.s, 'or_i is malleable')
        return TypeInfo(x.basic, o=x.z and zed.z, u=x.u and zed.u,
                        d=x.d or zed.d, s=x.s and zed.s,
                        f=x.f and zed.f,
                        e=(x.e and zed.f) or (zed.e and x.f), locks=locks)

    if kind == 'thresh':
        _require(1 <= node.value <= len(children), 'thresh threshold is invalid')
        _require(children and children[0].is_type('B', 'd', 'u'),
                 'thresh first argument must be Bdu')
        for child in children[1:]:
            _require(child.is_type('W', 'd', 'u'),
                     'thresh arguments after the first must be Wdu')
        non_signed = sum(1 for child in children if not child.s)
        _require(all(child.e for child in children) and non_signed <= node.value,
                 'thresh is malleable')
        zero_count = sum(1 for child in children if child.z)
        one_count = sum(1 for child in children if child.o)
        return TypeInfo('B', z=zero_count == len(children),
                        o=one_count == 1 and zero_count == len(children) - 1,
                        d=True, u=True, s=non_signed <= node.value - 1,
                        e=all(child.s for child in children), locks=locks)

    if kind in ('a', 's', 'c', 'd', 'v', 'j', 'n'):
        x = children[0]
        if kind == 'a':
            _require(x.basic == 'B', 'a: requires B')
            return TypeInfo('W', d=x.d, u=x.u, s=x.s, f=x.f, e=x.e, locks=locks)
        if kind == 's':
            _require(x.is_type('B', 'o'), 's: requires Bo')
            return TypeInfo('W', d=x.d, u=x.u, s=x.s, f=x.f, e=x.e, locks=locks)
        if kind == 'c':
            _require(x.basic == 'K', 'c: requires K')
            return TypeInfo('B', o=x.o, n=x.n, d=x.d, u=True,
                            s=True, f=x.f, e=x.e, locks=locks)
        if kind == 'd':
            _require(x.is_type('V', 'z'), 'd: requires Vz')
            return TypeInfo('B', o=True, n=True, d=True, s=x.s, e=True, locks=locks)
        if kind == 'v':
            _require(x.basic == 'B', 'v: requires B')
            return TypeInfo('V', z=x.z, o=x.o, n=x.n, s=x.s, f=True, locks=locks)
        if kind == 'j':
            _require(x.is_type('B', 'n'), 'j: requires Bn')
            return TypeInfo('B', o=x.o, n=True, d=True, u=x.u,
                            s=x.s, e=x.f, locks=locks)
        _require(x.basic == 'B', 'n: requires B')
        return TypeInfo('B', z=x.z, o=x.o, n=x.n, d=x.d, u=True,
                        s=x.s, f=x.f, e=x.e, locks=locks)

    raise PolicyTypeError("Unsupported AST node '{}'".format(kind))


def _walk(node):
    yield node
    for arg in node.args:
        if isinstance(arg, Node):
            for child in _walk(arg):
                yield child


def iter_policy_keys(node):
    """Yield key expressions in descriptor traversal order."""
    for item in _walk(node):
        if item.kind in ('pk_k', 'pk_h'):
            yield item.value
        elif item.kind in ('multi', 'multi_a'):
            for key in item.args:
                yield key


def policy_timelocks(node):
    return tuple((item.kind, item.value) for item in _walk(node)
                 if item.kind in ('older', 'after'))


def validate(node, context='wsh', require_signed=True, allow_hashlocks=False):
    info = analyze(node, context)
    _require(info.basic == 'B', 'Top-level Miniscript must have type B')
    if require_signed:
        _require(info.s, 'Every valid satisfaction must require a signature')

    if (info.locks & 1) and (info.locks & 2):
        raise UnsupportedPolicyError('Mixing height and time absolute locks is not supported')
    if (info.locks & 4) and (info.locks & 8):
        raise UnsupportedPolicyError('Mixing height and time relative locks is not supported')

    seen = set()
    branches_by_key = {}
    for item in _walk(node):
        if item.kind in ('sha256', 'hash256', 'ripemd160', 'hash160') and not allow_hashlocks:
            raise UnsupportedPolicyError('Hashlock policies are not supported')
        if item.kind == 'multi_a' and context != 'tr':
            raise PolicyTypeError('multi_a is only valid in Tapscript')
    for key in iter_policy_keys(node):
        ident = key.identity()
        if ident in seen:
            raise PolicyTypeError('A key expression is repeated in the policy')
        seen.add(ident)
        branch_set = set(key.branches)
        previous = branches_by_key.get(key.index, set())
        if previous.intersection(branch_set):
            raise PolicyTypeError('Derivation branches overlap for key @{}'.format(key.index))
        branches_by_key[key.index] = previous.union(branch_set)
    return info


def _push_data(data):
    size = len(data)
    if size < 0x4c:
        return bytes([size]) + data
    if size <= 0xff:
        return b'\x4c' + bytes([size]) + data
    if size <= 0xffff:
        return b'\x4d' + bytes([size & 0xff, size >> 8]) + data
    raise PolicyResourceError('Script push is too large')


def _script_num(value):
    if value == 0:
        return b'\x00'
    if 1 <= value <= 16:
        return bytes([OP_1 + value - 1])
    result = bytearray()
    while value:
        result.append(value & 0xff)
        value >>= 8
    if result[-1] & 0x80:
        result.append(0)
    return _push_data(bytes(result))


def _default_hash160(data):
    try:
        import trezorcrypto
        first = trezorcrypto.sha256(data).digest()
        return trezorcrypto.ripemd160(first).digest()
    except ImportError:  # pragma: no cover - CPython host tests
        import hashlib
        first = hashlib.sha256(data).digest()
        return hashlib.new('ripemd160', first).digest()


def _verify_last(script):
    replacements = {
        OP_EQUAL: OP_EQUALVERIFY,
        OP_CHECKSIG: OP_CHECKSIGVERIFY,
        OP_CHECKMULTISIG: OP_CHECKMULTISIGVERIFY,
        OP_NUMEQUAL: OP_NUMEQUALVERIFY,
    }
    if script and script[-1] in replacements:
        return script[:-1] + bytes([replacements[script[-1]]])
    return script + bytes([OP_VERIFY])


def _count_non_push_ops(script):
    """Count Script opcodes using the legacy P2WSH consensus rule."""
    position = 0
    count = 0
    length = len(script)
    while position < length:
        opcode = script[position]
        position += 1
        if opcode <= 0x4b:
            push_length = opcode
        elif opcode == 0x4c:
            if position >= length:
                raise PolicyTypeError('Compiled script contains a truncated push')
            push_length = script[position]
            position += 1
        elif opcode == 0x4d:
            if position + 2 > length:
                raise PolicyTypeError('Compiled script contains a truncated push')
            push_length = script[position] | (script[position + 1] << 8)
            position += 2
        else:
            push_length = 0
            if opcode > OP_16:
                count += 1
        position += push_length
        if position > length:
            raise PolicyTypeError('Compiled script contains a truncated push')
    return count


def compile_miniscript(node, key_resolver, branch, address_index, context='wsh',
                       hash160_fn=None, max_script_size=MAX_P2WSH_SCRIPT_SIZE):
    """Compile a validated AST.

    key_resolver is called as ``resolver(key_index, child_branch, index)`` and
    must return a compressed 33-byte key for P2WSH or a 32-byte x-only key for
    Tapscript.
    """
    if branch not in (0, 1):
        raise ValueError('branch must be receive (0) or change (1)')
    if not 0 <= address_index < 0x80000000:
        raise ValueError('address index must be unhardened')
    validate(node, context)
    hash160_fn = hash160_fn or _default_hash160

    def key_bytes(key):
        result = key_resolver(key.index, key.branches[branch], address_index)
        expected = 33 if context == 'wsh' else 32
        if not isinstance(result, (bytes, bytearray)) or len(result) != expected:
            raise PolicyTypeError('Key resolver returned an invalid public key')
        return bytes(result)

    def emit(item):
        kind = item.kind
        if kind == '0':
            return bytes([OP_0])
        if kind == '1':
            return bytes([OP_1])
        if kind == 'pk_k':
            return _push_data(key_bytes(item.value))
        if kind == 'pk_h':
            key = key_bytes(item.value)
            return bytes([OP_DUP, OP_HASH160]) + _push_data(hash160_fn(key)) + bytes([OP_EQUALVERIFY])
        if kind == 'older':
            return _script_num(item.value) + bytes([OP_CHECKSEQUENCEVERIFY])
        if kind == 'after':
            return _script_num(item.value) + bytes([OP_CHECKLOCKTIMEVERIFY])
        if kind in ('sha256', 'hash256', 'ripemd160', 'hash160'):
            opcode = {
                'sha256': OP_SHA256, 'hash256': OP_HASH256,
                'ripemd160': OP_RIPEMD160, 'hash160': OP_HASH160,
            }[kind]
            return (bytes([OP_SIZE]) + _script_num(32) + bytes([OP_EQUALVERIFY, opcode]) +
                    _push_data(unhexlify(item.value)) + bytes([OP_EQUAL]))
        if kind == 'andor':
            x, y, zed = item.args
            return emit(x) + bytes([OP_NOTIF]) + emit(zed) + bytes([OP_ELSE]) + emit(y) + bytes([OP_ENDIF])
        if kind == 'and_v':
            return emit(item.args[0]) + emit(item.args[1])
        if kind == 'and_b':
            return emit(item.args[0]) + emit(item.args[1]) + bytes([OP_BOOLAND])
        if kind == 'or_b':
            return emit(item.args[0]) + emit(item.args[1]) + bytes([OP_BOOLOR])
        if kind == 'or_c':
            return emit(item.args[0]) + bytes([OP_NOTIF]) + emit(item.args[1]) + bytes([OP_ENDIF])
        if kind == 'or_d':
            return emit(item.args[0]) + bytes([OP_IFDUP, OP_NOTIF]) + emit(item.args[1]) + bytes([OP_ENDIF])
        if kind == 'or_i':
            return bytes([OP_IF]) + emit(item.args[0]) + bytes([OP_ELSE]) + emit(item.args[1]) + bytes([OP_ENDIF])
        if kind == 'thresh':
            script = emit(item.args[0])
            for child in item.args[1:]:
                script += emit(child) + bytes([OP_ADD])
            return script + _script_num(item.value) + bytes([OP_EQUAL])
        if kind == 'multi':
            script = _script_num(item.value)
            for key in item.args:
                script += _push_data(key_bytes(key))
            return script + _script_num(len(item.args)) + bytes([OP_CHECKMULTISIG])
        if kind == 'multi_a':
            script = b''
            for position, key in enumerate(item.args):
                script += _push_data(key_bytes(key))
                script += bytes([OP_CHECKSIG if position == 0 else OP_CHECKSIGADD])
            return script + _script_num(item.value) + bytes([OP_NUMEQUAL])
        if kind == 'a':
            return bytes([OP_TOALTSTACK]) + emit(item.args[0]) + bytes([OP_FROMALTSTACK])
        if kind == 's':
            return bytes([OP_SWAP]) + emit(item.args[0])
        if kind == 'c':
            return emit(item.args[0]) + bytes([OP_CHECKSIG])
        if kind == 'd':
            return bytes([OP_DUP, OP_IF]) + emit(item.args[0]) + bytes([OP_ENDIF])
        if kind == 'v':
            return _verify_last(emit(item.args[0]))
        if kind == 'j':
            return bytes([OP_SIZE, OP_0NOTEQUAL, OP_IF]) + emit(item.args[0]) + bytes([OP_ENDIF])
        if kind == 'n':
            return emit(item.args[0]) + bytes([OP_0NOTEQUAL])
        raise PolicyTypeError("Cannot compile '{}'".format(kind))

    script = emit(node)
    if len(script) > max_script_size:
        raise PolicyResourceError('Compiled script exceeds {} bytes'.format(max_script_size))
    if context == 'wsh' and _count_non_push_ops(script) > MAX_P2WSH_OPS:
        raise PolicyResourceError('Compiled P2WSH script exceeds {} opcodes'.format(MAX_P2WSH_OPS))
    return script


def parse_miniscript(text, context='wsh'):
    node = Parser(text).parse()
    validate(node, context)
    return node
