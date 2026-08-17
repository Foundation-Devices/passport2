# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Test approval of multisig wallets proposed by PSBTs.

import flows
import uasyncio as asyncio
from flows import SignPsbtCommonFlow
from public_constants import MUSIG_ASK, MUSIG_TEMP_DEFAULT


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

        assert MUSIG_TEMP_DEFAULT == MUSIG_ASK
        return_value.write(b'OK')
    finally:
        flows.ImportMultisigWalletFlow = original_import_flow


asyncio.run(run_tests())
