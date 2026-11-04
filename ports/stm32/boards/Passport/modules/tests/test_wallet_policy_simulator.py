# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

from pathlib import Path

from fixtures.simulator import exec_file, simulator  # noqa: F401


def test_registered_policy_psbt_matches_in_micropython(exec_file):
    script = Path(__file__).parent / 'unit' / 'wallet_policy_psbt.py'
    exec_file(script)


def test_taproot_script_path_rejection_and_bip86_signing_in_micropython(exec_file):
    script = Path(__file__).parent / 'unit' / 'wallet_policy_taproot_psbt.py'
    exec_file(script)


def test_registered_policy_qr_backup_renders_and_returns(simulator):
    tests = Path(__file__).parent
    descriptor = (tests / 'host/fixtures/liana-multisig-policy.txt').read_text()
    script = (tests / 'unit/wallet_policy_qr.py').read_text()
    command, result = simulator.exec('POLICY_DESCRIPTOR = ' + repr(descriptor) + '\n' + script)
    assert command == 'resp', result.decode()
    assert result == b'OK'
