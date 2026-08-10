# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

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
    assert 'PASSPORT SPENDING PATH' in review
    assert 'This Passport can spend at any time' in review
    assert 'No waiting period applies' in review
    assert '6738 736C' in review
    assert 'AFTER THE RECOVERY DELAY' in review
    assert 'recovery key activates about 1 year after that coin confirms' in review
    assert 'Either key can then spend by itself' in review
    assert 'PASSPORT KEY - remains available' in review
    assert '52,596 blocks' in review
    assert '6738 736D' in review
    assert 'DELAY DETAILS' in review
    assert 'matched to the seed currently loaded on this Passport' in review
    assert 'remains available after the recovery key activates' in review
    assert 'restarts its timer' in review
    assert pages[-1].startswith('BACK UP THIS WALLET POLICY')
    assert 'cannot recreate this wallet policy' in pages[-1]
    assert 'Recovery 6738 736D\nactivates after about 1 year' in policy.format_confirmation()


def test_local_signer_name_is_used_and_escaped_without_changing_policy_semantics():
    policy = MiniscriptPolicy(
        'Liana Test', 'TBTC',
        'wsh(or_d(pk(@0/**),and_v(v:pkh(@1/**),older(52596))))',
        (key_info(0), key_info(1)), (0,), ('', 'Family ## Vault'))

    review = '\n'.join(policy.format_review_pages())
    assert 'Family #### Vault - becomes available' in review
    assert '6738 736D' in review


def test_simple_policy_signing_review_states_exact_passport_authority():
    policy = MiniscriptPolicy(
        'Liana Test', 'TBTC',
        'wsh(or_d(pk(@0/**),and_v(v:pkh(@1/**),older(52596))))',
        (key_info(0), key_info(1)), (0,), ('', 'Recovery key'))
    signing = '\n'.join(policy.format_signing_pages())
    assert 'WHAT YOUR SIGNATURE AUTHORIZES' in signing
    assert 'Immediate spending with this Passport' in signing
    assert 'The recovery path is not needed' in signing


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
    assert exact == '605,184 seconds (1,182 x 512)'
    assert 'each coin confirms' in detail

    assert describe_timelock('after', 840000)[:2] == (
        'block 840,000', 'absolute block height')
    assert describe_timelock('after', 1700000000)[:2] == (
        '2023-11-14 UTC', 'Unix timestamp 1,700,000,000')

    assert 'encoded as older(65537)' in describe_timelock('older', 65537)[1]


@pytest.mark.parametrize(('blocks', 'short', 'exact'), (
    (1, 'about 10 minutes', '1 block'),
    (6, 'about 1 hour', '6 blocks'),
    (144, 'about 1 day', '144 blocks'),
    (1008, 'about 1 week', '1,008 blocks'),
    (26298, 'about 6 months', '26,298 blocks'),
    (52596, 'about 1 year', '52,596 blocks'),
    (65535, 'about 1 year 3 months', '65,535 blocks'),
))
def test_relative_block_delays_scale_from_one_block_to_consensus_maximum(
        blocks, short, exact):
    assert describe_timelock('older', blocks)[:2] == (short, exact)


def test_time_based_relative_delay_and_absolute_date_are_unambiguous():
    assert describe_timelock('older', (1 << 22) | 1)[:2] == (
        'about 8 minutes', '512 seconds (1 x 512)')
    assert describe_timelock('older', (1 << 22) | 65535)[:2] == (
        'about 1 year 1 month', '33,553,920 seconds (65,535 x 512)')
    assert describe_timelock('after', 1798761600)[:2] == (
        '2027-01-01 UTC', 'Unix timestamp 1,798,761,600')
