# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

from pathlib import Path

from fixtures.simulator import exec_file  # noqa: F401


def test_registered_policy_psbt_matches_in_micropython(exec_file):
    script = Path(__file__).parent / 'unit' / 'wallet_policy_psbt.py'
    exec_file(script)


def test_registered_taproot_policy_psbt_matches_in_micropython(exec_file):
    script = Path(__file__).parent / 'unit' / 'wallet_policy_taproot_psbt.py'
    exec_file(script)
