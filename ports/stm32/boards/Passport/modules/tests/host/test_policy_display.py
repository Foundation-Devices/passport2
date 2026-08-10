# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

import builtins
import os
import sys
import types


MODULES = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if MODULES not in sys.path:
    sys.path.insert(0, MODULES)

if not hasattr(builtins, 'const'):
    builtins.const = lambda value: value
sys.modules.setdefault('public_constants', types.SimpleNamespace(
    AF_P2SH=8, AF_P2WSH=14, AF_P2WSH_P2SH=26))

from descriptor import append_checksum  # noqa: E402
from policy_display import describe_timelock  # noqa: E402
from wallet_policy import MiniscriptPolicy  # noqa: E402


XPUB = ('xpub6Br37sWxruYfT8ASpCjVHKGwgdnYFEn98DwiN76i2oyY6fgH1LAPmmDcF46x'
        'jxJr22gw4jmVjTE2E3URMnRPEPYyo1zoPSUba563ESMXCeb')
INTERNAL_KEY = ('79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798')


def key_info(index, purpose=48):
    fingerprint = '{:08x}'.format(0x6738736c + index)
    suffix = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'[index]
    return "[{}/{}'/0'/0'/2']{}{}".format(
        fingerprint, purpose, XPUB[:-1], suffix)


def test_liana_inheritance_is_explained_as_two_alternative_spend_paths():
    policy = MiniscriptPolicy(
        'Liana Test', 'TBTC',
        'wsh(or_d(pk(@0/**),and_v(v:pkh(@1/**),older(52596))))',
        (key_info(0), key_info(1)), (0,))

    pages = policy.format_review_pages()
    review = '\n'.join(pages)
    assert 'Simple inheritance' in pages[0]
    assert '2 ways to spend' in pages[0]
    assert 'SPEND ANYTIME' in review
    assert 'This Passport alone can spend' in review
    assert '6738 736C' in review
    assert 'RECOVER LATER' in review
    assert 'about 1 year' in review
    assert '52,596 blocks' in review
    assert '6738 736D' in review
    assert 'THE DELAY IS PER COIN' in review
    assert 'restarts its timer' in review
    assert pages[-1].startswith('BACKUP REQUIRED')
    assert 'Recovery 6738 736D\nafter about 1 year' in policy.format_confirmation()


def test_canonical_full_descriptor_and_short_check_are_available_for_comparison():
    policy = MiniscriptPolicy(
        'Check', 'BTC', 'wsh(pk(@0/**))', (key_info(0),), (0,))
    expected = append_checksum('wsh(pk({}/**))'.format(key_info(0)))
    assert policy.full_descriptor() == expected
    assert policy.descriptor_check() == expected[-8:].upper()
    details = policy.format_details()
    assert expected in details
    assert 'Internal Policy ID' in details


def test_threshold_tree_does_not_expand_combinations_and_flags_passport_bypass():
    policy = MiniscriptPolicy(
        'Team Recovery', 'BTC',
        'wsh(or_d(multi(2,@0/**,@1/**,@2/**),'
        'and_v(v:pk(@3/**),older(1008))))',
        tuple(key_info(index) for index in range(4)), (0,))
    review = '\n'.join(policy.format_review_pages())
    assert 'Custom wallet policy' in review
    assert '2 OF 3 KEYS' in review
    assert 'This Passport - 6738 736C' in review
    assert 'Key 2 - 6738 736D' in review
    assert 'Wait about 1 week' in review
    assert 'Key 4 - 6738 736F' in review
    assert 'Recovery key - 6738 736F' not in review
    # The other two primary keys can satisfy the 2-of-3 without Passport.
    assert review.count('This path does not require Passport.') == 2
    assert '2 paths can spend without this Passport' in review


def test_maximum_key_threshold_stays_linear_and_names_every_signer():
    key_count = 15
    template = 'wsh(multi(8,{}))'.format(','.join(
        '@{}/**'.format(index) for index in range(key_count)))
    policy = MiniscriptPolicy(
        'Maximum Signers', 'BTC', template,
        tuple(key_info(index) for index in range(key_count)), (0,))

    pages = policy.format_review_pages()
    review = '\n'.join(pages)
    assert '8 OF 15 KEYS' in review
    for index in range(key_count):
        assert '{:04X} {:04X}'.format(
            (0x6738736c + index) >> 16,
            (0x6738736c + index) & 0xffff) in review
    # The review lists each signer once; it never enumerates C(15, 8) paths.
    assert len(review) < 1600
    assert 'This path does not require Passport' in review


def test_threshold_conditions_are_rendered_without_opaque_miniscript():
    policy = MiniscriptPolicy(
        'Condition Threshold', 'BTC',
        'wsh(thresh(2,pk(@0/**),s:pk(@1/**),a:pk(@2/**)))',
        tuple(key_info(index) for index in range(3)), (0,))
    review = '\n'.join(policy.format_review_pages())
    assert '2 OF 3 CONDITIONS' in review
    assert 'Advanced condition' not in review


def test_conditional_policy_is_rendered_structurally_without_false_simplification():
    policy = MiniscriptPolicy(
        'Conditional', 'BTC',
        'wsh(andor(pk(@0/**),pk(@1/**),pk(@2/**)))',
        tuple(key_info(index) for index in range(3)), (0,))
    review = '\n'.join(policy.format_review_pages())
    assert 'CONDITIONAL PATH' in review
    assert '\n  IF\n' in review
    assert '\n  THEN ALSO\n' in review
    assert '\n  OTHERWISE\n' in review
    assert 'Review the conditional branches carefully' in review
    assert '1 conditional path requires detailed review' in review


def test_taproot_key_paths_are_first_class_spending_paths():
    fixed = MiniscriptPolicy(
        'Fixed Internal', 'BTC',
        'tr({},pk(@0/**))'.format(INTERNAL_KEY),
        (key_info(0, 86),), (0,))
    fixed_review = '\n'.join(fixed.format_review_pages())
    assert '2 ways to spend' in fixed_review
    assert 'TAPROOT KEY PATH' in fixed_review
    assert 'can bypass every script condition' in fixed_review
    assert 'cannot verify that no one controls this key' in fixed_review

    dynamic = MiniscriptPolicy(
        'Dynamic Internal', 'BTC', 'tr(@0/**,pk(@1/**))',
        (key_info(0, 86), key_info(1, 86)), (1,))
    dynamic_review = '\n'.join(dynamic.format_review_pages())
    assert 'Key 1 - 6738 736C can spend without using any script-path conditions' \
        in dynamic_review
    assert 'This path does not require Passport' in dynamic_review


def test_height_and_time_locks_get_human_and_exact_descriptions():
    short, exact, detail = describe_timelock('older', 52596)
    assert short == 'about 1 year'
    assert exact == '52,596 blocks'
    assert 'each coin confirms' in detail

    short, exact, detail = describe_timelock('older', (1 << 22) | 1182)
    assert short == 'about 1 week'
    assert exact == '1,182 BIP68 time units'
    assert 'each coin confirms' in detail

    assert describe_timelock('after', 840000)[:2] == (
        'block 840,000', 'absolute block height')
    assert describe_timelock('after', 1700000000)[:2] == (
        'Unix time 1,700,000,000', 'absolute timestamp')

    assert 'encoded as older(65537)' in describe_timelock('older', 65537)[1]
