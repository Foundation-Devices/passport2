# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Exercise imported PSBT review methods in the standard simulator harness.

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

    def render_address(self, script):
        return 'bc1qtest'


class MockFlow(SignPsbtCommonFlow):
    def __init__(self, psbt):
        self.psbt = psbt
        self.chain = MockChain()


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
            review = list(MockFlow(psbt).review_pages())
            text = review[-1]
            assert 'Network Fee' not in text
            assert sum('Any other cosigner' in page for page in review) == 1
            assert '1-of-{} Multisig'.format(policy[1]) in text
            assert 'Any other cosigner can spend' in text
            assert 'including change' in text
            assert 'without approval from this wallet' in text


return_value.write(b'OK')
