# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Test trusted-display rendering for PSBT outputs.

from flows.sign_psbt_common_flow import SignPsbtCommonFlow
from styles.colors import HIGHLIGHT_TEXT_HEX
from utils import escape_text, recolor, stylize_address


class MockChain:
    def render_value(self, value):
        return (str(value), 'sats')

    def render_address(self, script):
        return 'OP_RETURN:\n{}'.format(script)


class MockFlow:
    chain = MockChain()


class MockAddressChain(MockChain):
    def render_address(self, script):
        return script


class MockAddressFlow:
    chain = MockAddressChain()


class MockOutput:
    def __init__(self, value, message):
        self.nValue = value
        self.scriptPubKey = message


def assert_op_return_output(value, message):
    rendered = SignPsbtCommonFlow.render_output(MockFlow(), MockOutput(value, message))

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
rendered = SignPsbtCommonFlow.render_output(MockFlow(), MockOutput(1, malicious_message))
assert escape_text(malicious_message) in rendered
assert rendered.count('\n{}\n'.format(amount_heading)) == 1
assert rendered.count('\n{}\n'.format(message_heading)) == 1
assert rendered.count('\n{}\n'.format(destination_heading)) == 0
assert malicious_message not in rendered

address = 'bc1qvaliddestination'
rendered = SignPsbtCommonFlow.render_output(MockAddressFlow(), MockOutput(42, address))
assert rendered == '\n{}\n42 sats\n\n{}\n{}'.format(
    amount_heading, destination_heading, stylize_address(address))

# PSBT failures are reported through a recolor-enabled label, and psbt.py raises
# plenty of messages carrying a literal '#'. Unescaped, LVGL reads that as the
# start of a colour tag and drops the index that follows it.
indexed = 'Missing redeem/witness script for input #3'
rendered = SignPsbtCommonFlow.invalid_psbt_text(MockFlow(), ValueError(indexed))
assert rendered == 'Invalid PSBT: {}'.format(escape_text(indexed))
assert 'input ##3' in rendered
# Every '#' is doubled, which is what makes LVGL draw it rather than read a
# colour tag. Checking the invariant beats checking for a literal, because the
# escaped form of a tag still contains the unescaped form as a substring.
assert '#' not in rendered.replace('##', '')

# A message with no '#' must come through untouched.
plain = 'Network fee bigger than the amount you are sending'
assert SignPsbtCommonFlow.invalid_psbt_text(MockFlow(), ValueError(plain)) == \
    'Invalid PSBT: {}'.format(plain)

# And recolor markup inside an exception cannot open a colour span.
injected = SignPsbtCommonFlow.invalid_psbt_text(MockFlow(), ValueError(amount_heading))
assert '#' not in injected.replace('##', '')

return_value.write(b'OK')
