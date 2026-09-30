# SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundation.xyz>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Run unit tests in the Unix MP build.

import pytest
from fixtures.simulator import *


@pytest.fixture
def test(exec_file):
    def doit(file):
        return exec_file('unit/' + file)

    return doit


def test_error_codes(test):
    assert test('error_codes.py') == b'OK'


def test_ecdsa_bindings(test):
    assert test('ecdsa_bindings.py') == b'OK'


def test_ext_settings(test):
    assert test('ext_settings.py') == b'OK'


def test_passphrase_length(test):
    assert test('passphrase_length.py') == b'OK'


def test_crypto_api_surface(test):
    assert test('crypto_api_surface.py') == b'OK'


def test_firmware_pubkey(test):
    assert test('firmware_pubkey.py') == b'OK'


def test_psbt_sighash(test):
    assert test('psbt_sighash.py') == b'OK'


def test_bip39_prefix_matching(test):
    assert test('bip39_prefix_matching.py') == b'OK'


def test_hdnode_blank(test):
    assert test('hdnode_blank.py') == b'OK'


def test_psbt_unsigned_txn(test):
    assert test('psbt_unsigned_txn.py') == b'OK'


def test_ur_derived_key(test):
    assert test('ur_derived_key.py') == b'OK'


def test_psbt_multisig_approval(test):
    assert test('psbt_multisig_approval.py') == b'OK'


def test_seedqr_codec(test):
    assert test('seedqr_codec.py') == b'OK'


def test_multisig_save_task(test):
    assert test('multisig_save_task.py') == b'OK'


def test_ui(test):
    assert test('ui.py') == b'OK'


def test_sign_psbt(test):
    assert test('sign_psbt.py') == b'OK'


def test_op_return_rendering(test):
    assert test('op_return_rendering.py') == b'OK'


def test_foundation(test):
    assert test('foundation.py') == b'OK'


def test_psbt_amounts(test):
    assert test('psbt_amounts.py') == b'OK'


def test_multisig_xpub_validation(test):
    assert test('multisig_xpub_validation.py') == b'OK'


def test_psbt_fee(test):
    assert test('psbt_fee.py') == b'OK'


def test_unchained(test):
    assert test('unchained.py') == b'OK'


def test_restore_backup(test):
    assert test('restore_backup.py') == b'OK'


def test_bip322(test):
    assert test('bip322.py') == b'OK'


def test_single_line_message(test):
    assert test('single_line_message.py') == b'OK'
