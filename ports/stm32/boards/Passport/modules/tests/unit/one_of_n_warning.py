# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Exercise imported PSBT review methods in the standard simulator harness.

import pages
import uasyncio as asyncio
from psbt import psbtObject
from serializations import CTxOut
from flows.sign_psbt_common_flow import SignPsbtCommonFlow


class MockWallet:
    def __init__(self, policy):
        self.M, self.N = policy


class MockOutput:
    def __init__(self, is_change):
        self.is_change = is_change
        self.validations = []

    def validate(self, *args):
        self.validations.append(args)


class MockPSBT:
    active_policy = None
    my_xfp = 123
    total_value_out = 1000
    fee_is_verified = True

    def __init__(self, policy, change):
        self.active_multisig = MockWallet(policy) if policy else None
        self.outputs = [MockOutput(False)]
        self.values = [1000]
        if change is not None:
            self.outputs.append(MockOutput(True))
            self.values = [1000 - change, change]
        self.warnings = []
        self.self_send = False
        self.change_checks = []

    def output_iter(self):
        for index, value in enumerate(self.values):
            yield index, CTxOut(value, b'')

    def calculate_fee(self):
        return 1

    def consider_dangerous_change(self, xfp):
        self.change_checks.append(xfp)


class MockChain:
    def render_value(self, value):
        return str(value), 'sats'


class MockFlow:
    chain = MockChain()
    header = 'Transaction Info'
    show_policy_authorization = 'authorize'
    render_warnings = SignPsbtCommonFlow.render_warnings

    def __init__(self, psbt):
        self.psbt = psbt
        self.events = []

    def back(self):
        self.events.append('back')

    def goto(self, state):
        self.events.append(state)


# None means there is no change output at all; zero retains a zero-value one.
for policy in (None, (1, 1), (1, 2), (1, 15), (2, 3), (3, 3)):
    for change in (None, 0, 500, 1000):
        psbt = MockPSBT(policy, change)
        psbtObject.consider_outputs(psbt)
        assert len(psbt.outputs) == (1 if change is None else 2)
        for index, output in enumerate(psbt.outputs):
            assert len(output.validations) == 1
            idx, txo, xfp, wallet, active_policy = output.validations[0]
            assert active_policy is None
            assert idx == index and txo.nValue == psbt.values[index]
            assert xfp == psbt.my_xfp and wallet is psbt.active_multisig
        assert psbt.change_checks == [psbt.my_xfp]
        assert psbt.self_send == (change == 1000)
        expected = policy is not None and policy[0] == 1 and policy[1] > 1
        assert len(psbt.warnings) == int(expected)
        if expected:
            text = MockFlow(psbt).render_warnings()
            assert '1-of-{} Multisig'.format(policy[1]) in text
            assert 'Any other cosigner can spend' in text
            assert 'including change' in text
            assert 'without approval from this wallet' in text


class MockPage:
    approve = False
    flow = None

    def __init__(self, text, **kwargs):
        assert text == self.flow.render_warnings()
        assert '1-of-2 Multisig' in text

    async def show(self):
        self.flow.events.append('review')
        return self.approve


async def run_tests():
    original_page = pages.LongTextPage
    try:
        pages.LongTextPage = MockPage
        for approve in (False, True):
            psbt = MockPSBT((1, 2), None)
            psbtObject.consider_outputs(psbt)
            flow = MockFlow(psbt)
            MockPage.flow = flow
            MockPage.approve = approve
            await SignPsbtCommonFlow.show_warnings(flow)
            assert flow.events == ['review', 'authorize' if approve else 'back']
    finally:
        pages.LongTextPage = original_page


asyncio.run(run_tests())
return_value.write(b'OK')
