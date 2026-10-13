# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

import common
import lvgl as lv
import microns
import pages
import uasyncio as asyncio
from display import Display
from flows.sign_psbt_common_flow import SignPsbtCommonFlow
from pages.long_text_page import LongTextPage
from psbt import psbtOutputProxy
from serializations import CTxOut
from styles.colors import HIGHLIGHT_TEXT_HEX
from uio import BytesIO
from utils import escape_text, recolor, stylize_address


class Transaction:
    active_policy = None
    fee_is_verified = True

    def __init__(self, changes=(None, True, None, True), self_send=False, warnings=()):
        self.outputs = []
        for index, change in enumerate(changes):
            output = psbtOutputProxy(BytesIO(b'\x00'), index)
            if change is not None:
                output.is_change = change
            self.outputs.append(output)
        self.self_send = self_send
        self.warnings = warnings

    def output_iter(self):
        output = CTxOut()
        for index in range(len(self.outputs)):
            output.nValue = index + 1
            output.scriptPubKey = 'destination-{}'.format(index)
            yield index, output

    def calculate_fee(self):
        return 42


class Chain:
    def render_value(self, value):
        return str(value), 'sats'

    def render_address(self, script):
        return script


class ReviewFlow(SignPsbtCommonFlow):
    def __init__(self, transaction):
        original_settings = common.settings
        common.settings = {}
        try:
            super().__init__(0)
        finally:
            common.settings = original_settings
        self.psbt = transaction
        self.chain = Chain()
        self.state = self.show_transaction_details
        self.signed = False

    async def sign_transaction(self):
        self.signed = True
        self.set_result('signed')


class ReviewPage:
    texts = []
    responses = []

    def __init__(self, text, **kwargs):
        assert kwargs['require_scroll_to_end']
        self.texts.append(text)

    async def show(self):
        assert self.responses, 'Unexpected review page'
        return self.responses.pop(0)


class ErrorPage:
    errors = []

    def __init__(self, text):
        self.errors.append(text)

    async def show(self):
        return True


class QuestionPage:
    questions = []

    def __init__(self, text, **kwargs):
        self.questions.append(text)

    async def show(self):
        return False


def render(transaction):
    return list(ReviewFlow(transaction).review_pages())


warnings = [('Big Fee', 'Large fee'), ('Suspicious Change Outputs', 'Output #1: unusual path'),
            ('1-of-2 Multisig', 'Any other cosigner can spend'), ('Other #warning', '#ff0000 message#')]
transaction = Transaction(warnings=warnings)
texts = render(transaction)
destinations = [stylize_address('destination-{}'.format(index)) for index in range(4)]
assert len(texts) == 9
assert texts[0].startswith(recolor(HIGHLIGHT_TEXT_HEX, 'Output 1/2')) and destinations[0] in texts[0]
assert texts[1].startswith(recolor(HIGHLIGHT_TEXT_HEX, 'Output 2/2')) and destinations[2] in texts[1]
assert 'Change Amount' in texts[2] and '6 sats' in texts[2]
assert texts[3].startswith(recolor(HIGHLIGHT_TEXT_HEX, 'Change 1/2')) and destinations[1] in texts[3]
assert texts[4].startswith(recolor(HIGHLIGHT_TEXT_HEX, 'Change 2/2')) and destinations[3] in texts[4]
assert 'Network Fee' in texts[5] and '42 sats' in texts[5] and 'Big Fee' in texts[5]
assert 'Suspicious Change Outputs' in texts[6] and 'Output ##1' in texts[6]
assert '1-of-2 Multisig' in texts[7]
assert escape_text('Other #warning') in texts[8] and escape_text('#ff0000 message#') in texts[8]
for index in range(3):
    assert texts[6 + index].startswith(recolor(HIGHLIGHT_TEXT_HEX, 'Warning {}/3'.format(index + 1)))
assert all(sum(destination in text for destination in destinations) <= 1 for text in texts)
for label in ('Big Fee', 'Huge Fee', 'Unverified Fee'):
    fee_transaction = Transaction(changes=(False,), warnings=[(label, 'Fee warning')])
    fee_transaction.fee_is_verified = label != 'Unverified Fee'
    fee_page = render(fee_transaction)[-1]
    assert 'Network Fee' in fee_page and label in fee_page
    assert ('42 sats' in fee_page) == fee_transaction.fee_is_verified
    assert ('Unverified' in fee_page) != fee_transaction.fee_is_verified

self_send = render(Transaction(changes=(True, True), self_send=True))
assert len(self_send) == 3
assert self_send[0].startswith(recolor(HIGHLIGHT_TEXT_HEX, 'Self-Send 1/2'))
assert self_send[1].startswith(recolor(HIGHLIGHT_TEXT_HEX, 'Self-Send 2/2'))
assert destinations[0] in self_send[0] and destinations[1] in self_send[1]
assert len(render(Transaction(changes=(False,)))) == 3
assert render(Transaction(changes=(False,)))[1] == 'No change'


async def run_flow_tests():
    original_page, original_error = pages.LongTextPage, pages.ErrorPage
    original_question = pages.QuestionPage
    pages.LongTextPage, pages.ErrorPage = ReviewPage, ErrorPage
    pages.QuestionPage = QuestionPage
    try:
        for stop in range(len(texts)):
            flow = ReviewFlow(transaction)
            ReviewPage.texts, ReviewPage.responses = [], [True] * stop + [None]
            assert await flow.run() is None
            assert not flow.signed
            assert ReviewPage.texts == texts[:stop + 1]

        for stop in range(len(texts)):
            flow = ReviewFlow(transaction)
            ReviewPage.texts = []
            ReviewPage.responses = [True] * stop + [False] * (stop + 1)
            assert await flow.run() is None
            assert not flow.signed
            assert ReviewPage.texts == texts[:stop + 1] + list(reversed(texts[:stop]))

        flow = ReviewFlow(transaction)
        ReviewPage.texts = []
        ReviewPage.responses = [True, True, False] + [True] * (len(texts) - 1)
        assert await flow.run() == 'signed'
        assert flow.signed
        assert ReviewPage.texts == texts[:3] + texts[1:]
        assert not ReviewPage.responses

        # Declining cancellation must return to review without requesting a signature.
        flow.done = False
        flow.signed = False
        await SignPsbtCommonFlow.sign_transaction(flow)
        assert QuestionPage.questions == ['Sign transaction?', 'Cancel this transaction?']
        ReviewPage.texts, ReviewPage.responses = [], [False, None]
        assert await flow.run() is None
        assert ReviewPage.texts == texts[-1:] + texts[-2:-1]
        assert not flow.signed

        for case in (Transaction(changes=(True, True), self_send=True),
                     Transaction(changes=(False,)),
                     Transaction(changes=(None,)),
                     Transaction(changes=(None, False, True), warnings=warnings),
                     Transaction(changes=(None,) * 100, warnings=warnings)):
            expected = render(case)
            flow = ReviewFlow(case)
            ReviewPage.texts, ReviewPage.responses = [], [True] * len(expected)
            assert await flow.run() == 'signed'
            assert ReviewPage.texts == expected
        assert not ErrorPage.errors
    finally:
        pages.LongTextPage, pages.ErrorPage = original_page, original_error
        pages.QuestionPage = original_question


class ReviewUI:
    def set_left_micron(self, micron):
        pass

    def set_right_micron(self, micron):
        self.right_micron = micron


class Keypad:
    def set_active_page(self, page):
        pass


def test_scroll_gate():
    Display()
    original_ui, original_keypad = common.ui, common.keypad
    common.ui, common.keypad = ReviewUI(), Keypad()
    parent = lv.obj(lv.scr_act())
    parent.set_size(230, 220)
    parent.set_style_pad_all(0, 0)
    parent.set_flex_flow(lv.FLEX_FLOW.COLUMN)
    group = lv.group_create()
    try:
        for text, overflow in (('Short text', False), ('Long warning\n' * 50, True)):
            page = LongTextPage(text=text, require_scroll_to_end=True)
            page.mount(parent)
            page.attach(group)
            container = page.container.lvgl_root
            assert (container.get_scroll_bottom() > 0) == overflow
            assert (common.ui.right_micron is None) == overflow
            page.right_action(True)
            assert not page.done
            page.right_action(False)
            assert page.done != overflow
            if overflow:
                container.scroll_to_y(container.get_scroll_bottom() // 2, lv.ANIM.OFF)
                page.right_action(False)
                assert not page.done
                container.scroll_to_y(container.get_scroll_y() + container.get_scroll_bottom(), lv.ANIM.OFF)
                assert common.ui.right_micron == microns.Forward
                container.scroll_to_y(0, lv.ANIM.OFF)
                page.right_action(False)
                assert page.done and page.result is True
            page.detach()
            page.unmount()

        page = LongTextPage(text='Long warning\n' * 50)
        page.mount(parent)
        page.attach(group)
        page.right_action(False)
        assert page.done and page.result is True
        page.detach()
        page.unmount()
    finally:
        parent.delete()
        group._del()
        common.ui, common.keypad = original_ui, original_keypad


asyncio.run(run_flow_tests())
test_scroll_gate()
return_value.write(b'OK')
