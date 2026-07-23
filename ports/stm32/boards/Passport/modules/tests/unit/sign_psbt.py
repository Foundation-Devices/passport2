# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Test trusted-display rendering for PSBT outputs.

from flows.sign_psbt_common_flow import SignPsbtCommonFlow


class FakeChain:
    def render_value(self, value):
        return (str(value), 'sats')

    def render_address(self, script):
        return 'OP_RETURN:\n{}'.format(script)


class FakeFlow:
    chain = FakeChain()


class FakeOutput:
    def __init__(self, value, message):
        self.nValue = value
        self.scriptPubKey = message


def assert_op_return_output(value, message):
    rendered = SignPsbtCommonFlow.render_output(FakeFlow(), FakeOutput(value, message))

    amount_label = rendered.find('Amount')
    amount = rendered.find('{} sats'.format(value))
    message_label = rendered.find('Message')
    payload = rendered.find(message)

    assert -1 not in (amount_label, amount, message_label, payload)
    assert amount_label < amount < message_label < payload


assert_op_return_output(0, 'zero-value-message')
assert_op_return_output(50000000, 'payment-id-12345')

return_value.write(b'OK')
