# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Value sent to OP_RETURN outputs is reported as a warning during review.

import chains
import common
from flows.sign_psbt_common_flow import SignPsbtCommonFlow
from psbt import psbtObject
from serializations import CTxOut

P2WPKH = b'\x00\x14' + (b'\x11' * 20)
OP_RETURN = b'\x6a\x04memo'
BARE_OP_RETURN = b'\x6a'


class MockOutput:
    is_change = False

    def validate(self, *args):
        pass


class MockPSBT:
    active_policy = None
    active_multisig = None
    my_xfp = 123
    fee_is_verified = True

    def __init__(self, outputs):
        self.txouts = [CTxOut(value, script) for value, script in outputs]
        self.outputs = [MockOutput() for _ in outputs]
        self.total_value_out = sum(value for value, _ in outputs)
        self.warnings = []
        self.self_send = False

    def output_iter(self):
        for index, txout in enumerate(self.txouts):
            yield index, txout

    def calculate_fee(self):
        return 1

    def consider_dangerous_change(self, xfp):
        pass


class MockChain:
    def render_value(self, value):
        return str(value), 'sats'

    def render_address(self, script):
        return 'OP_RETURN:\nmemo' if script[:1] == b'\x6a' else 'bc1qtest'


class MockFlow(SignPsbtCommonFlow):
    def __init__(self, psbt):
        self.psbt = psbt
        self.chain = MockChain()


def burn_warnings(outputs):
    psbt = MockPSBT(outputs)
    psbtObject.consider_outputs(psbt)
    return psbt, [warning for warning in psbt.warnings if warning[0] == 'Burned Amount']


def rendered(value):
    return ' '.join(chains.current_chain().render_value(value))


# chains.current_chain() and render_value() read settings, which the harness
# leaves unset. Supply defaults (BTC, BTC units) and restore them afterwards.
original_settings = common.settings
common.settings = {}
try:
    # Nothing is burned when OP_RETURN outputs carry no value, or there are none.
    for outputs in ([(1000, P2WPKH), (0, OP_RETURN)],
                    [(1000, P2WPKH), (0, BARE_OP_RETURN)],
                    [(1000, P2WPKH)]):
        assert burn_warnings(outputs)[1] == []

    # A valued OP_RETURN is reported with its amount, bare or carrying data.
    for script in (OP_RETURN, BARE_OP_RETURN):
        _, warnings = burn_warnings([(1000, P2WPKH), (100, script)])
        assert len(warnings) == 1
        assert warnings[0][1] == '{} is sent to OP_RETURN and can never be spent.'.format(rendered(100))

    # Several valued OP_RETURN outputs produce one warning for the total.
    _, warnings = burn_warnings([(100, OP_RETURN), (1000, P2WPKH), (50, BARE_OP_RETURN)])
    assert len(warnings) == 1
    assert rendered(150) in warnings[0][1]

    # Review gives the warning a page of its own, after the network fee page.
    psbt, _ = burn_warnings([(1000, P2WPKH), (100, OP_RETURN)])
    pages = list(MockFlow(psbt).review_pages())
    fee_page = [index for index, page in enumerate(pages) if 'Network Fee' in page]
    burn_page = [index for index, page in enumerate(pages) if 'Burned Amount' in page]
    assert len(fee_page) == 1 and len(burn_page) == 1
    assert fee_page[0] < burn_page[0]
    assert 'Warning 1/1' in pages[burn_page[0]]
    assert 'can never be spent' in pages[burn_page[0]]
finally:
    common.settings = original_settings

return_value.write(b'OK')
