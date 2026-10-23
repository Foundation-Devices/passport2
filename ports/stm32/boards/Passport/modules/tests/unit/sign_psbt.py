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


def assert_op_return_output(value, message, shown=None):
    rendered = SignPsbtCommonFlow.render_output(MockFlow(), MockOutput(value, message))

    amount_label = rendered.find('Amount')
    amount = rendered.find('{} sats'.format(value))
    destination_label = rendered.find('Destination')
    destination = rendered.find('\nOP_RETURN\n')
    message_label = rendered.find('Message')
    payload = rendered.rfind(message if shown is None else shown)

    assert -1 not in (amount_label, amount, destination_label, destination, message_label, payload)
    assert amount_label < amount < destination_label < destination < message_label < payload
    return rendered


assert_op_return_output(0, 'zero-value-message')
assert_op_return_output(50000000, 'payment-id-12345')

# The message is never blank: no payload says so, and a payload with nothing the
# review font can draw (it only carries printable ASCII) falls back to hex.
assert assert_op_return_output(0, '', '(empty)').endswith('\n(empty)')
assert assert_op_return_output(1, '‘', 'e28098').endswith('\ne28098')
assert assert_op_return_output(1, '한글', 'ed959ceab880').endswith('\ned959ceab880')
assert assert_op_return_output(1, ' \n ', '200a20').endswith('\n200a20')
assert assert_op_return_output(1, '\x00A', '0041').endswith('\n0041')
assert assert_op_return_output(1, 'A\x00B', '410042').endswith('\n410042')
assert assert_op_return_output(1, 'A\x00', '4100').endswith('\n4100')
# One drawable character is enough to show the text itself.
assert assert_op_return_output(1, 'a‘b').endswith('\na‘b')

amount_heading = recolor(HIGHLIGHT_TEXT_HEX, 'Amount')
message_heading = recolor(HIGHLIGHT_TEXT_HEX, 'Message')
destination_heading = recolor(HIGHLIGHT_TEXT_HEX, 'Destination')
malicious_message = '{}\n0.00000001 BTC\n\n{}\nbc1qattacker'.format(
    amount_heading, destination_heading)
rendered = SignPsbtCommonFlow.render_output(MockFlow(), MockOutput(1, malicious_message))
assert escape_text(malicious_message) in rendered
# Forged headings in the message are escaped, so only the real ones remain.
assert rendered.count('\n{}\n'.format(amount_heading)) == 1
assert rendered.count('\n{}\n'.format(message_heading)) == 1
assert rendered.count('\n{}\n'.format(destination_heading)) == 1
assert rendered.index('\n{}\nOP_RETURN\n'.format(destination_heading)) < rendered.index(message_heading)
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
