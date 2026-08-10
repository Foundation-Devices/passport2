# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

import hashlib
import os
import sys

import pytest


MODULES = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if MODULES not in sys.path:
    sys.path.insert(0, MODULES)

from miniscript import (Parser, _count_non_push_ops, analyze,  # noqa: E402
                        compile_miniscript, validate)
from policy_errors import (PolicyParseError, PolicyResourceError,  # noqa: E402
                           PolicyTypeError, UnsupportedPolicyError)


KEYS = tuple(bytes.fromhex(key) for key in (
    '031b84c5567b126440995d3ed5aaba0565d71e1834604819ff9c17f5e9d5dd078f',
    '024d4b6cd1361032ca9bd2aeb9d900aa4d45d9ead80ac9423374c451a7254d0766',
    '02531fe6068134503d2723133227c867ac8fa6c83c537e9a44c3c5bdbdcb1fe337',
    '03462779ad4aad39514614751a71085f2f10e1c7a593e4e030efb5b8721ce55b0b',
))


def resolve(index, branch, address_index):
    assert branch in (0, 1)
    assert address_index == 0
    return KEYS[index]


GOLDEN_SCRIPTS = (
    (
        'multi(2,@0/**,@1/**,@2/**,@3/**)',
        '5221031b84c5567b126440995d3ed5aaba0565d71e1834604819ff9c17f5e9d5dd078f'
        '21024d4b6cd1361032ca9bd2aeb9d900aa4d45d9ead80ac9423374c451a7254d0766'
        '2102531fe6068134503d2723133227c867ac8fa6c83c537e9a44c3c5bdbdcb1fe337'
        '2103462779ad4aad39514614751a71085f2f10e1c7a593e4e030efb5b8721ce55b0b54ae',
    ),
    (
        'or_d(pk(@0/**),and_v(v:multi(2,@1/**,@2/**,@3/**),older(65535)))',
        '21031b84c5567b126440995d3ed5aaba0565d71e1834604819ff9c17f5e9d5dd078fac736452'
        '21024d4b6cd1361032ca9bd2aeb9d900aa4d45d9ead80ac9423374c451a7254d0766'
        '2102531fe6068134503d2723133227c867ac8fa6c83c537e9a44c3c5bdbdcb1fe337'
        '2103462779ad4aad39514614751a71085f2f10e1c7a593e4e030efb5b8721ce55b0b53af'
        '03ffff00b268',
    ),
    (
        'thresh(2,pk(@0/**),s:pk(@1/**),sln:older(12960))',
        '21031b84c5567b126440995d3ed5aaba0565d71e1834604819ff9c17f5e9d5dd078fac'
        '7c21024d4b6cd1361032ca9bd2aeb9d900aa4d45d9ead80ac9423374c451a7254d0766ac93'
        '7c63006702a032b29268935287',
    ),
)


@pytest.mark.parametrize('expression, expected', GOLDEN_SCRIPTS)
def test_compile_matches_independent_golden_vectors(expression, expected):
    node = Parser(expression).parse()
    info = validate(node)
    assert info.basic == 'B'
    assert info.s
    assert compile_miniscript(node, resolve, 0, 0).hex() == expected


def test_explicit_receive_change_branches_are_passed_to_resolver():
    calls = []

    def tracking_resolver(index, branch, address_index):
        calls.append((index, branch, address_index))
        return KEYS[index]

    node = Parser('multi(2,@0/<4;9>/*,@1/<5;8>/*)').parse()
    compile_miniscript(node, tracking_resolver, 1, 7)
    assert calls == [(0, 9, 7), (1, 8, 7)]


@pytest.mark.parametrize('expression', (
    '',
    'pk(@0/**)garbage',
    'pk(@0/0/*)',
    'pk(@0/<0;0>/*)',
    'pk(@00/**)',
    'unknown(@0/**)',
    'older(0)',
    'older(2147483648)',
    'multi(0,@0/**)',
    'multi(2,@0/**)',
))
def test_malformed_or_invalid_policies_fail(expression):
    with pytest.raises((PolicyParseError, PolicyTypeError, PolicyResourceError)):
        node = Parser(expression).parse()
        validate(node)


def test_hashlocks_are_valid_syntax_but_not_in_phase_a_profile():
    node = Parser('and_v(v:pk(@0/**),sha256(' + '11' * 32 + '))').parse()
    with pytest.raises(UnsupportedPolicyError, match='Hashlock'):
        validate(node)


def test_overlapping_derivation_branches_are_rejected():
    node = Parser('multi(1,@0/<0;1>/*,@0/<1;2>/*)').parse()
    with pytest.raises(PolicyTypeError, match='overlap'):
        validate(node)


def test_disjoint_derivation_branches_for_same_xpub_are_allowed():
    node = Parser('multi(1,@0/<0;1>/*,@0/<2;3>/*)').parse()
    assert analyze(node).basic == 'B'
    validate(node)


def test_duplicate_key_expression_is_rejected():
    node = Parser('multi(1,@0/**,@0/**)').parse()
    with pytest.raises(PolicyTypeError, match='repeated'):
        validate(node)


def test_parser_depth_and_size_are_bounded():
    with pytest.raises(PolicyResourceError):
        Parser('v:' * 18 + 'pk(@0/**)').parse()
    with pytest.raises(PolicyResourceError):
        Parser('pk(@0/**)' + 'x' * 513).parse()


def test_key_resolver_must_return_compressed_p2wsh_key():
    node = Parser('pk(@0/**)').parse()
    with pytest.raises(PolicyTypeError, match='invalid public key'):
        compile_miniscript(node, lambda *_: bytes(32), 0, 0)


def test_opcode_counter_ignores_pushed_bytes():
    script = bytes([33]) + KEYS[0] + bytes([0xac, 2, 0xac, 0xac, 0x69])
    assert _count_non_push_ops(script) == 2


# Independently cross-checked against Bitcoin Core's Miniscript implementation
# and embit.  Hashes keep the additional wrapper/fragment vectors compact.
CROSS_IMPLEMENTATION_VECTORS = (
    ('pkh(@0/**)', 25, '6f1b349d7fed5240ad719948529e8b06abf038438f9b523820489375af513a3f'),
    ('and_v(v:pk(@0/**),pk(@1/**))', 70,
     'b0eaafe0b01383e92f7b3c9643d4da835943440b897bcb44fbbbd4b0b957b69a'),
    ('or_i(pk(@0/**),pk(@1/**))', 73,
     '24b1fdb679c11186fc70cd17d82bd5e8fae3148dce7614379c793f0f5a5badd9'),
    ('andor(pk(@0/**),pk(@1/**),pk(@2/**))', 108,
     '103d50da989a23cb5282db73c209ea067338c4bd7fe7e5a6d1e821d5bfaa161d'),
    ('and_b(pk(@0/**),a:pk(@1/**))', 73,
     '09f13aaaf994c1d804f2b54d046533f4d41b4f74bf1c460c8d0f21662785b7e1'),
    ('or_b(pk(@0/**),a:pk(@1/**))', 73,
     '8b8918ece3065e4c19b2a12f1d259d49db8dfdfd6c5a06eb5b7a640fc3da5283'),
    ('t:or_c(pk(@0/**),v:pk(@1/**))', 73,
     '5605ce9b362bd078da557895e086f51a703dca71e6ef2b5d5ef950d613e3e31e'),
    ('thresh(2,pk(@0/**),s:pk(@1/**),a:pk(@2/**))', 112,
     '373f8dbe10414589afcd76526cd8b754035d6ee038b38d5d5691545801b0b45e'),
    ('j:and_v(v:pk(@0/**),older(2016))', 43,
     '13f2f90e699ab9798a7833197c266b15c8eacf333ea73aa14937d9651ab62140'),
    ('c:and_v(v:older(16),pk_k(@0/**))', 38,
     '4fb1e1b5ea866245f6ffd23721d8d39540fc942b86a416c2e65c3b1dc9902570'),
    ('c:or_i(pk_k(@0/**),pk_k(@1/**))', 72,
     '061a8d8a21ac89746425b8ec00fd6bac5f79641ac12155288e32a7a1fa17c797'),
)


@pytest.mark.parametrize('expression, expected_length, expected_hash',
                         CROSS_IMPLEMENTATION_VECTORS)
def test_compile_matches_cross_implementation_vectors(
        expression, expected_length, expected_hash):
    script = compile_miniscript(Parser(expression).parse(), resolve, 0, 0)
    assert len(script) == expected_length
    assert hashlib.sha256(script).hexdigest() == expected_hash
