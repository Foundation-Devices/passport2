# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import sys


MODULES = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if MODULES not in sys.path:
    sys.path.insert(0, MODULES)

from psbt_display import (  # noqa: E402
    format_psbt_error, format_signed_psbt_message, format_utc_time, timelock_warnings)


def test_missing_input_script_explains_coordinator_action_before_technical_detail():
    technical = 'Missing redeem/witness script for input #0'
    friendly, detail = format_psbt_error(technical)
    assert 'missing information Passport needs to verify how an input can be spent' in friendly
    assert 'Re-export it from your wallet coordinator' in friendly
    assert 'witness or redeem script' in friendly
    assert detail == technical
    assert technical not in friendly


def test_missing_output_script_explains_change_verification():
    technical = 'Missing redeem/witness script for output #1'
    friendly, detail = format_psbt_error(technical)
    assert 'verify a change output' in friendly
    assert detail == technical


def test_registered_policy_mismatch_tells_user_not_to_sign():
    technical = 'Wallet policy change output does not match: script mismatch'
    friendly, detail = format_psbt_error(technical)
    assert 'Do not sign' in friendly
    assert 'create the transaction again' in friendly
    assert detail == technical


def test_input_policy_mismatch_gets_the_same_fail_closed_guidance():
    technical = 'Input #0: PSBT scripts and derivations do not match the registered policy'
    friendly, detail = format_psbt_error(technical)
    assert 'does not match the registered wallet policy and Passport key' in friendly
    assert 'Do not sign' in friendly
    assert detail == technical


def test_unmapped_error_is_preserved_without_redundant_details_page():
    assert format_psbt_error('Transaction is already fully signed.') == (
        'Transaction is already fully signed.', None)


def test_partial_psbt_success_explains_the_coordinator_handoff():
    text = format_signed_psbt_message('/card/payment-part.psbt')
    assert text.startswith('Passport signature added')
    assert 'Updated PSBT\n/card/payment-part.psbt' in text
    assert 'collect any remaining signatures, finalize, and broadcast' in text
    assert 'finalized transaction' not in text


def test_complete_psbt_success_distinguishes_psbt_from_final_transaction():
    text = format_signed_psbt_message(
        '/card/payment-signed.psbt', '/card/payment-final.txn', 'abc123')
    assert 'Return the updated PSBT to your wallet coordinator to finalize and broadcast' in text
    assert 'also saved a finalized transaction that is ready to broadcast' in text
    assert '/card/payment-final.txn' in text
    assert 'Transaction ID\nabc123' in text


# Sequences a normal wallet sets: final, final with locktime, and RBF.
FINAL = 0xffffffff
LOCKTIME_ENABLED = 0xfffffffe
RBF = 0xfffffffd
# A relative lock of 144 blocks, and of 169 units of 512 seconds (about a day).
BLOCKS_144 = 144
ABOUT_A_DAY = (1 << 22) | 169
DISABLED_LOCK = (1 << 31) | 144


def test_normal_wallet_timelocks_are_not_flagged():
    # Anti-fee-sniping sets the current block height, which Passport can't tell from a future one.
    assert timelock_warnings(2, 925000, [RBF, RBF]) == []
    assert timelock_warnings(2, 0, [FINAL, LOCKTIME_ENABLED, RBF]) == []
    assert timelock_warnings(1, 0, [0]) == []


def test_lock_to_a_date_is_flagged_with_the_date():
    warnings = timelock_warnings(2, 1798761600, [FINAL, RBF])
    assert warnings == [('Timelock', "This transaction can't be confirmed until after 2027-01-01 00:00 UTC.")]


def test_lock_to_a_date_is_ignored_when_every_input_is_final():
    assert timelock_warnings(2, 1798761600, [FINAL, FINAL]) == []


def test_relative_locks_are_listed_per_input():
    warnings = timelock_warnings(2, 0, [RBF, BLOCKS_144, ABOUT_A_DAY, 1])
    assert len(warnings) == 1
    title, text = warnings[0]
    assert title == 'Relative Timelock'
    assert text.endswith('\n\nInput 2: 144 blocks\nInput 3: about 1 day\nInput 4: 1 block')
    assert 'Input 1' not in text


def test_relative_locks_need_version_2_and_a_non_zero_value():
    assert timelock_warnings(1, 0, [BLOCKS_144, ABOUT_A_DAY]) == []
    assert timelock_warnings(2, 0, [0, 1 << 22, DISABLED_LOCK]) == []


def test_both_kinds_of_lock_are_flagged_together():
    titles = [title for title, _ in timelock_warnings(2, 1798761600, [BLOCKS_144])]
    assert titles == ['Timelock', 'Relative Timelock']


def test_utc_time_matches_the_standard_library():
    import datetime
    for timestamp in (500000000, 951782400, 951868799, 1798761600, 4102444800, 4107542400, 0xffffffff):
        expected = datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc).strftime('%Y-%m-%d %H:%M')
        assert format_utc_time(timestamp) == expected
