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
from policy_display import compatible_path_indexes, describe_timelock  # noqa: E402
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
    assert pages[0].startswith('Liana Test\n\nSimple inheritance')
    assert 'Spend with Passport' in review
    assert 'Passport can authorize spending by itself' in review
    assert 'No recovery delay is required' in review
    assert '6738 736C' in review
    assert 'Spend with the recovery key' in review
    assert 'Recovery key can spend by itself about 1 year after each coin confirms' in review
    assert 'Passport can still spend by itself after the recovery key becomes available' in review
    assert '52,596 blocks' in review
    assert '6738 736D' in review
    assert 'How the recovery delay works' in review
    assert 'matches the seed currently loaded on Passport' in review
    assert 'restarts its timer' in review
    assert pages[-1].startswith('Back up this policy')
    assert 'Your seed recovers this Passport key, not the policy' in pages[-1]
    assert pages[-1].endswith('Keep a separate copy.')
    assert ('Recovery 6738 736D\ncan spend by itself about 1 year after each coin confirms'
            in policy.format_confirmation())


def test_local_signer_name_is_used_and_escaped_without_changing_policy_semantics():
    policy = MiniscriptPolicy(
        'Liana Test', 'TBTC',
        'wsh(or_d(pk(@0/**),and_v(v:pkh(@1/**),older(52596))))',
        (key_info(0), key_info(1)), (0,), ('', 'Family ## Vault'))

    review = '\n'.join(policy.format_review_pages())
    assert 'Family #### Vault can spend by itself' in review
    assert '6738 736D' in review


def test_simple_policy_signing_review_states_exact_passport_authority():
    policy = MiniscriptPolicy(
        'Liana Test', 'TBTC',
        'wsh(or_d(pk(@0/**),and_v(v:pkh(@1/**),older(52596))))',
        (key_info(0), key_info(1)), (0,), ('', 'Recovery key'))
    signing = '\n'.join(policy.format_signing_pages())
    assert 'Signing path' in signing
    assert 'Wallet\nLiana Test' in signing
    assert 'Passport is authorizing this transaction with its own key' in signing
    assert 'No recovery delay is required' in signing
    assert 'Passport key\n6738 736C' in signing
    assert 'The recovery key is not being used' in signing


def test_canonical_full_descriptor_and_short_check_are_available_for_comparison():
    policy = MiniscriptPolicy(
        'Check', 'BTC', 'wsh(pk(@0/**))', (key_info(0),), (0,))
    expected = append_checksum('wsh(pk({}/**))'.format(key_info(0)))
    assert policy.full_descriptor() == expected
    assert policy.descriptor_check() == expected[-8:].upper()
    details = policy.format_details()
    assert expected in details
    assert 'Internal policy ID' in details


def test_threshold_tree_does_not_expand_combinations_and_flags_passport_bypass():
    policy = MiniscriptPolicy(
        'Team Recovery', 'BTC',
        'wsh(or_d(multi(2,@0/**,@1/**,@2/**),'
        'and_v(v:pk(@3/**),older(1008))))',
        tuple(key_info(index) for index in range(4)), (0,))
    review = '\n'.join(policy.format_review_pages())
    assert 'Custom wallet policy' in review
    assert 'Any 2 of 3 keys must sign' in review
    assert 'This Passport\n6738 736C' in review
    assert 'Key 2\n6738 736D' in review
    assert 'Available after about 1 week' in review
    assert 'Key 4\n6738 736F' in review
    assert 'Recovery key\n6738 736F' not in review
    # The other two primary keys can satisfy the 2-of-3 without Passport.
    assert review.count('This Passport is optional.') == 1
    assert review.count('This Passport is not used.') == 1
    assert 'Spend now (2-of-3)\nOptional' in review
    assert 'After about 1 week (1-of-1)\nNot used' in review


def test_maximum_key_threshold_stays_linear_and_names_every_signer():
    key_count = 15
    template = 'wsh(multi(8,{}))'.format(','.join(
        '@{}/**'.format(index) for index in range(key_count)))
    policy = MiniscriptPolicy(
        'Maximum Signers', 'BTC', template,
        tuple(key_info(index) for index in range(key_count)), (0,))

    pages = policy.format_review_pages()
    review = '\n'.join(pages)
    assert 'Any 8 of 15 keys must sign' in review
    for index in range(key_count):
        assert '{:04X} {:04X}'.format(
            (0x6738736c + index) >> 16,
            (0x6738736c + index) & 0xffff) in review
    # The review lists each signer once; it never enumerates C(15, 8) paths.
    assert len(review) < 1600
    assert 'This Passport is optional.' in review


def test_threshold_conditions_are_rendered_without_opaque_miniscript():
    policy = MiniscriptPolicy(
        'Condition Threshold', 'BTC',
        'wsh(thresh(2,pk(@0/**),s:pk(@1/**),a:pk(@2/**)))',
        tuple(key_info(index) for index in range(3)), (0,))
    review = '\n'.join(policy.format_review_pages())
    assert 'Any 2 of 3 keys must sign' in review
    assert 'Advanced condition' not in review


def test_liana_multisig_shows_immediate_path_first_with_compact_key_blocks():
    policy = MiniscriptPolicy(
        'Liana Multisig', 'TBTC',
        'wsh(or_i('
        'and_v(v:thresh(2,pkh(@0/<2;3>/*),a:pkh(@1/<2;3>/*),'
        'a:pkh(@2/<0;1>/*)),older(52596)),'
        'and_v(v:pk(@0/<0;1>/*),pk(@1/<0;1>/*))))',
        tuple(key_info(index) for index in range(3)), (0,),
        ('', 'HOT KEY', 'BACKUP PASSPORT'))

    pages = policy.format_review_pages()
    immediate = pages[1]
    delayed = pages[2]

    assert immediate.startswith('Spend now')
    assert 'Both keys must sign' in immediate
    assert 'This Passport\n6738 736C' in immediate
    assert 'HOT KEY\n6738 736D' in immediate

    assert delayed.startswith('Delayed spending')
    assert 'Available after about 1 year' in delayed
    assert 'Exact delay: 52,596 blocks' in delayed
    assert 'Any 2 of 3 keys must sign' in delayed
    assert 'BACKUP PASSPORT\n6738 736E' in delayed
    assert 'All of' not in delayed
    assert 'conditions' not in delayed
    assert '- This Passport -' not in delayed
    assert '- HOT KEY -' not in delayed
    assert '- BACKUP PASSPORT -' not in delayed
    assert 'Wait about' not in delayed
    assert 'This path does not require Passport' not in delayed
    assert 'This Passport is optional.' in delayed

    passport_role = pages[3]
    assert passport_role == (
        'This Passport\n\nSpend now (2-of-2)\nMust sign\n\n'
        'After about 1 year (2-of-3)\nOptional')

    signing = policy.format_signing_pages()[0]
    assert signing.startswith('Wallet\nLiana Multisig')
    assert ('This Passport will sign:\nSpend now (2-of-2): required\n'
            'After about 1 year (2-of-3): optional') in signing
    assert 'Key: 6738 736C' in signing
    assert 'Your wallet app chooses which valid option completes the transaction.' in signing
    assert 'reviewed paths' not in signing
    assert 'wallet coordinator' not in signing

    # The final sequence used by ordinary RBF transactions disables BIP68, so
    # the 52,596-block recovery branch cannot finalize this transaction.
    immediate_only = compatible_path_indexes(
        policy, tx_version=2, lock_time=0, sequence=0xfffffffd)
    assert immediate_only == (0,)
    selected = policy.format_signing_pages(immediate_only)[0]
    assert 'Spend now (2-of-2)' in selected
    assert 'Both keys must sign' in selected
    assert 'This Passport\n6738 736C' in selected
    assert 'HOT KEY\n6738 736D' in selected
    assert 'After about 1 year' not in selected
    assert 'optional' not in selected

    # A version-2 transaction with a matching height sequence leaves both the
    # immediate and delayed branches available until witness finalization.
    assert compatible_path_indexes(
        policy, tx_version=2, lock_time=0, sequence=52596) == (0, 1)
    assert compatible_path_indexes(
        policy, tx_version=1, lock_time=0, sequence=52596) == (0,)


def test_conditional_policy_is_rendered_structurally_without_false_simplification():
    policy = MiniscriptPolicy(
        'Conditional', 'BTC',
        'wsh(andor(pk(@0/**),pk(@1/**),pk(@2/**)))',
        tuple(key_info(index) for index in range(3)), (0,))
    review = '\n'.join(policy.format_review_pages())
    assert 'Conditional path' in review
    assert '\n  If\n' in review
    assert '\n  Then also\n' in review
    assert '\n  Otherwise\n' in review
    assert 'Review the conditional branches carefully' in review


def test_taproot_key_paths_are_first_class_spending_paths():
    fixed = MiniscriptPolicy(
        'Fixed Internal', 'BTC',
        'tr({},pk(@0/**))'.format(INTERNAL_KEY),
        (key_info(0, 86),), (0,))
    fixed_review = '\n'.join(fixed.format_review_pages())
    assert '2 ways to spend' in fixed_review
    assert 'Taproot key path' in fixed_review
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


def test_absolute_path_compatibility_requires_matching_locktime_and_sequence():
    policy = MiniscriptPolicy(
        'Absolute Recovery', 'BTC',
        'wsh(or_i(pk(@0/**),and_v(v:pk(@1/**),after(840000))))',
        (key_info(0), key_info(1)), (0,))

    # The immediate path remains possible in every case. The absolute path is
    # excluded until nLockTime reaches its height and an input is non-final.
    assert compatible_path_indexes(policy, 2, 839999, 0xfffffffe) == (0,)
    assert compatible_path_indexes(policy, 2, 840000, 0xffffffff) == (0,)
    assert compatible_path_indexes(policy, 2, 840000, 0xfffffffe) == (0, 1)
    # A timestamp locktime cannot satisfy a block-height policy.
    assert compatible_path_indexes(policy, 2, 1700000000, 0xfffffffe) == (0,)


def test_relative_path_compatibility_rejects_unit_and_value_mismatches():
    policy = MiniscriptPolicy(
        'Relative Recovery', 'BTC',
        'wsh(or_i(pk(@0/**),and_v(v:pk(@1/**),older(1008))))',
        (key_info(0), key_info(1)), (0,))

    assert compatible_path_indexes(policy, 2, 0, 1007) == (0,)
    assert compatible_path_indexes(policy, 2, 0, 1008) == (0, 1)
    assert compatible_path_indexes(policy, 2, 0, (1 << 22) | 1008) == (0,)
