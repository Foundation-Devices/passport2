# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Exercise message review and signing without keys or interactive pages.

import pages
import stash
import utils
import uasyncio as asyncio
import flows.sign_electrum_message_flow as electrum
from flows.health_check_common_flow import HealthCheckCommonFlow


class MockReviewPage:
    texts = []

    def __init__(self, text, **kwargs):
        self.texts.append(text)

    async def show(self):
        return True


class MockSensitiveValues:
    def __enter__(self):
        self.chain = self
        return self

    def __exit__(self, *args):
        pass

    def derive_path(self, path):
        return path

    def address(self, node, addr_type):
        return '1BoatSLRHtKNngkdXEeobR76b53LETtpyT'


class MockFlow:
    subpath = "m/44'/0'/0'/0/0"
    addr_type = 0
    normal_signing = True
    do_sign = 'sign-electrum'
    sign_health_check = 'sign-microsd'
    show_signed = 'show-signed'
    format_signature = 'format-signature'

    def goto(self, state, **kwargs):
        self.next_state = state

    def set_result(self, result):
        raise AssertionError('Unexpected rejection')


signed_messages = []


async def mock_sign_spinner(label, task, args):
    assert task is electrum.sign_text_file_task
    signed_messages.append(args[0])
    return (b'signature', args[3], None)


async def run_tests():
    original_text_page = pages.LongTextPage
    original_question_page = pages.LongQuestionPage
    original_electrum_text_page = electrum.LongTextPage
    original_electrum_question_page = electrum.LongQuestionPage
    original_sensitive_values = stash.SensitiveValues
    original_spinner = utils.spinner_task
    original_electrum_spinner = electrum.spinner_task
    try:
        pages.LongTextPage = electrum.LongTextPage = MockReviewPage
        pages.LongQuestionPage = electrum.LongQuestionPage = MockReviewPage
        stash.SensitiveValues = MockSensitiveValues
        utils.spinner_task = electrum.spinner_task = mock_sign_spinner

        cases = (
            ('literal # and ## hashes', 'literal ## and #### hashes'),
            ('#ff0000 red#', '##ff0000 red##'),
            ('before #00ff00 green# after #', 'before ##00ff00 green## after ##'),
        )
        for message, displayed in cases:
            for is_electrum in (True, False):
                flow = MockFlow()
                flow.message = flow.text = message
                MockReviewPage.texts = []
                before = len(signed_messages)
                if is_electrum:
                    await electrum.SignElectrumMessageFlow.show_message(flow)
                    assert flow.next_state == flow.do_sign
                else:
                    await HealthCheckCommonFlow.show_message(flow)
                    assert flow.next_state == flow.sign_health_check
                assert MockReviewPage.texts[0] == '\n' + displayed
                assert len(MockReviewPage.texts) == 2
                assert len(signed_messages) == before
                assert flow.message == flow.text == message
                if is_electrum:
                    await electrum.SignElectrumMessageFlow.do_sign(flow)
                else:
                    await HealthCheckCommonFlow.sign_health_check(flow)
                assert len(signed_messages) == before + 1
                assert signed_messages[-1] == message
        return_value.write(b'OK')
    finally:
        pages.LongTextPage = original_text_page
        pages.LongQuestionPage = original_question_page
        electrum.LongTextPage = original_electrum_text_page
        electrum.LongQuestionPage = original_electrum_question_page
        stash.SensitiveValues = original_sensitive_values
        utils.spinner_task = original_spinner
        electrum.spinner_task = original_electrum_spinner


asyncio.run(run_tests())
