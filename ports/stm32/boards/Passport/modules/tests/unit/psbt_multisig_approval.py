# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Test approval of multisig wallets proposed by PSBTs.

import common
import flows
import uasyncio as asyncio
from flows import SignPsbtCommonFlow
from public_constants import MUSIG_ASK, MUSIG_SKIP
from utils import get_multisig_policy


class FakeImportMultisigWalletFlow:
    result = None
    calls = 0

    def __init__(self, wallet):
        assert wallet == 'proposed-wallet'
        FakeImportMultisigWalletFlow.calls += 1

    async def run(self):
        return self.result


class FakePsbt:
    def __init__(self, needs_approval):
        self.multisig_import_needs_approval = needs_approval
        self.active_multisig = 'proposed-wallet'


class FakeSettings:
    temporary_mode = True

    def __init__(self, policy=None):
        self.policy = policy

    def get(self, key, default=None):
        if key == 'temporary_seed':
            return 'temporary-seed'
        if key == 'multisig_policy' and self.policy is not None:
            return self.policy
        return default


class FakeSignFlow:
    def __init__(self, needs_approval):
        self.psbt = FakePsbt(needs_approval)
        self.show_transaction_details = 'transaction-details'
        self.completed = False
        self.result = 'unset'
        self.next_state = None

    def set_result(self, result):
        self.completed = True
        self.result = result

    def goto(self, state):
        self.next_state = state


async def run_tests():
    original_import_flow = flows.ImportMultisigWalletFlow
    original_settings = common.settings

    try:
        flows.ImportMultisigWalletFlow = FakeImportMultisigWalletFlow

        FakeImportMultisigWalletFlow.result = False
        FakeImportMultisigWalletFlow.calls = 0
        flow = FakeSignFlow(needs_approval=True)
        await SignPsbtCommonFlow.check_multisig_import(flow)
        assert FakeImportMultisigWalletFlow.calls == 1
        assert flow.completed
        assert flow.result is None
        assert flow.next_state is None

        FakeImportMultisigWalletFlow.result = True
        FakeImportMultisigWalletFlow.calls = 0
        flow = FakeSignFlow(needs_approval=True)
        await SignPsbtCommonFlow.check_multisig_import(flow)
        assert FakeImportMultisigWalletFlow.calls == 1
        assert not flow.completed
        assert flow.next_state == flow.show_transaction_details

        FakeImportMultisigWalletFlow.calls = 0
        flow = FakeSignFlow(needs_approval=False)
        await SignPsbtCommonFlow.check_multisig_import(flow)
        assert FakeImportMultisigWalletFlow.calls == 0
        assert not flow.completed
        assert flow.next_state == flow.show_transaction_details

        common.settings = FakeSettings()
        assert get_multisig_policy() == MUSIG_ASK

        common.settings = FakeSettings(policy=MUSIG_SKIP)
        assert get_multisig_policy() == MUSIG_SKIP

        return_value.write(b'OK')
    finally:
        flows.ImportMultisigWalletFlow = original_import_flow
        common.settings = original_settings


asyncio.run(run_tests())
