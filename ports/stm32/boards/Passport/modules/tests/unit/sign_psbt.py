# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Test trusted-display rendering for PSBT outputs.

from flows.sign_psbt_common_flow import SignPsbtCommonFlow
from styles.colors import HIGHLIGHT_TEXT_HEX
from utils import escape_text, recolor, stylize_address


class FakeChain:
    def render_value(self, value):
        return (str(value), 'sats')

    def render_address(self, script):
        return 'OP_RETURN:\n{}'.format(script)


class FakeFlow:
    chain = FakeChain()


class FakeAddressChain(FakeChain):
    def render_address(self, script):
        return script


class FakeAddressFlow:
    chain = FakeAddressChain()


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

amount_heading = recolor(HIGHLIGHT_TEXT_HEX, 'Amount')
message_heading = recolor(HIGHLIGHT_TEXT_HEX, 'Message')
destination_heading = recolor(HIGHLIGHT_TEXT_HEX, 'Destination')
malicious_message = '{}\n0.00000001 BTC\n\n{}\nbc1qattacker'.format(
    amount_heading, destination_heading)
rendered = SignPsbtCommonFlow.render_output(FakeFlow(), FakeOutput(1, malicious_message))
assert escape_text(malicious_message) in rendered
assert rendered.count('\n{}\n'.format(amount_heading)) == 1
assert rendered.count('\n{}\n'.format(message_heading)) == 1
assert rendered.count('\n{}\n'.format(destination_heading)) == 0
assert malicious_message not in rendered

address = 'bc1qvaliddestination'
rendered = SignPsbtCommonFlow.render_output(FakeAddressFlow(), FakeOutput(42, address))
assert rendered == '\n{}\n42 sats\n\n{}\n{}'.format(
    amount_heading, destination_heading, stylize_address(address))

return_value.write(b'OK')
