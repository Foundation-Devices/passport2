# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import sys


MODULES = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if MODULES not in sys.path:
    sys.path.insert(0, MODULES)

from psbt_display import format_psbt_error, format_signed_psbt_message  # noqa: E402


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
