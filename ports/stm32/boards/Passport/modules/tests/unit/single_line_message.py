# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Test validation of the microSD signmessage format before review or signing.

import pages
import uasyncio as asyncio
from flows.health_check_common_flow import HealthCheckCommonFlow
from public_constants import AF_CLASSIC, AF_P2WPKH


class MockErrorPage:
    errors = []

    def __init__(self, text):
        self.errors.append(text)

    async def show(self):
        return True


class MockFlow:
    show_message = 'review'
    sign_health_check = 'sign'

    def __init__(self, lines, normal_signing):
        self.lines = lines
        self.normal_signing = normal_signing
        self.addr_type = AF_CLASSIC
        self.next_state = None
        self.result = 'unset'

    def goto(self, state):
        self.next_state = state

    def set_result(self, result):
        self.result = result


async def run_tests():
    original_error_page = pages.ErrorPage
    path = "m/84'/0'/0'/0/0"
    try:
        pages.ErrorPage = MockErrorPage
        for normal_signing in (True, False):
            MockErrorPage.errors = []
            flow = MockFlow(['signmessage ' + path + ' ascii:'], normal_signing)
            await HealthCheckCommonFlow.validate_lines(flow)
            assert MockErrorPage.errors == ['Message is empty.']
            assert flow.result is None
            assert flow.next_state is None

        for normal_signing in (True, False):
            for invalid_path in ('x', 'm', 'm/foo', ''):
                MockErrorPage.errors = []
                flow = MockFlow(['signmessage ' + invalid_path + ' ascii:hi'], normal_signing)
                await HealthCheckCommonFlow.validate_lines(flow)
                assert MockErrorPage.errors
                assert flow.result is None
                assert flow.next_state is None

            # Strict text checks also apply to health checks, deliberately.
            for message in (' leading', 'trailing ', 'four    spaces', 'line\nbreak', 'a\x00b', '\u00e9'):
                MockErrorPage.errors = []
                flow = MockFlow(['signmessage ' + path + ' ascii:' + message], normal_signing)
                await HealthCheckCommonFlow.validate_lines(flow)
                assert MockErrorPage.errors
                assert flow.result is None
                assert flow.next_state is None

            # A normalized path drives address selection; health-check mode
            # intentionally accepts this format without entering message review.
            MockErrorPage.errors = []
            flow = MockFlow(['signmessage m/84h/0h/0h/0/0 ascii:hello'], normal_signing)
            await HealthCheckCommonFlow.validate_lines(flow)
            assert not MockErrorPage.errors
            assert flow.subpath == path
            assert flow.addr_type == AF_P2WPKH
            assert flow.next_state == (flow.show_message if normal_signing else flow.sign_health_check)

        for message in ('x', 'message with spaces and ascii: inside'):
            MockErrorPage.errors = []
            flow = MockFlow(['signmessage ' + path + ' ascii:' + message], True)
            await HealthCheckCommonFlow.validate_lines(flow)
            assert not MockErrorPage.errors
            assert flow.text == message
            assert flow.subpath == path
            assert flow.addr_type == AF_P2WPKH
            assert flow.next_state == flow.show_message
            assert flow.result == 'unset'

        MockErrorPage.errors = []
        flow = MockFlow(['signmessage ' + path + ' hex:00'], True)
        await HealthCheckCommonFlow.validate_lines(flow)
        assert MockErrorPage.errors == ['Message format is invalid.']
        assert flow.result is None
        assert flow.next_state is None
        return_value.write(b'OK')
    finally:
        pages.ErrorPage = original_error_page


asyncio.run(run_tests())
