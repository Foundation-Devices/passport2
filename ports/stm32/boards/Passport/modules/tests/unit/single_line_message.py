# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Test validation of the microSD signmessage format before review or signing,
# and what a health check accepts.

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

    def __init__(self, lines, normal_signing, service=None):
        self.data = '\n'.join(lines)
        self.normal_signing = normal_signing
        self.service = service
        self.addr_type = AF_CLASSIC
        self.next_state = None
        self.result = 'unset'

    def goto(self, state):
        self.next_state = state

    def set_result(self, result):
        self.result = result


async def validate(lines, normal_signing, service=None):
    MockErrorPage.errors = []
    flow = MockFlow(lines, normal_signing, service)
    await HealthCheckCommonFlow.validate_lines(flow)
    return flow


def assert_refused(flow, error=None):
    assert MockErrorPage.errors if error is None else MockErrorPage.errors == [error]
    assert flow.result is None
    assert flow.next_state is None


async def run_tests():
    original_error_page = pages.ErrorPage
    path = "m/84'/0'/0'/0/0"
    try:
        pages.ErrorPage = MockErrorPage

        # The Electrum format, which only message signing accepts.
        assert_refused(await validate(['signmessage ' + path + ' ascii:'], True), 'Message is empty.')

        for invalid_path in ('x', 'm', 'm/foo', ''):
            assert_refused(await validate(['signmessage ' + invalid_path + ' ascii:hi'], True))

        for message in (' leading', 'trailing ', 'four    spaces', 'line\rbreak', 'a\x00b', '\u00e9'):
            assert_refused(await validate(['signmessage ' + path + ' ascii:' + message], True))

        # A normalized path drives address selection.
        flow = await validate(['signmessage m/84h/0h/0h/0/0 ascii:hello'], True)
        assert not MockErrorPage.errors
        assert flow.subpath == path
        assert flow.addr_type == AF_P2WPKH
        assert flow.next_state == flow.show_message

        for message in ('x', 'message with spaces and ascii: inside'):
            flow = await validate(['signmessage ' + path + ' ascii:' + message], True)
            assert not MockErrorPage.errors
            assert flow.text == message
            assert flow.subpath == path
            assert flow.addr_type == AF_P2WPKH
            assert flow.next_state == flow.show_message
            assert flow.result == 'unset'

        assert_refused(await validate(['signmessage ' + path + ' hex:00'], True), 'Message format is invalid.')

        flow = await validate(('signmessage ' + path + ' ascii:line\nbreak').splitlines(), True)
        assert not MockErrorPage.errors
        assert flow.text == 'line\nbreak'
        assert flow.next_state == flow.show_message

        # The legacy 2- and 3-line format takes the same empty-message check.
        # A file beginning with a newline splits to an empty first line, which
        # used to reach validate_sign_text() and raise IndexError on text[0].
        for normal_signing in (True, False):
            for lines in (['', path], ['', path, 'p2wpkh']):
                assert_refused(await validate(lines, normal_signing), 'Message is empty.')

        # The legacy format still works, and still takes its address type from
        # the third line rather than from the path.
        for lines in (['hello', path], ['hello', path, 'p2pkh'], ['signmessage hello', path, 'p2wpkh']):
            flow = await validate(lines, True)
            assert not MockErrorPage.errors
            assert flow.text == lines[0]
            assert flow.subpath == path
            assert flow.next_state == flow.show_message
            assert flow.result == 'unset'

        # A legacy file whose path is unusable is still refused by the shared
        # validator, not by the path check that only the Envoy format runs.
        assert_refused(await validate(['hello', 'not-a-path'], True))

        # Health checks: the formats Casa and Theya send are signed without
        # review, for the keys those services use.
        accepted = (
            ('Casa', ['5078313b-5f7d-4e2a-a974-e658237cbd44', 'm/49/0/1/0/0']),
            ('Casa', ['5078313b-5f7d-4e2a-a974-e658237cbd44', "m/45'/0/0/1/7"]),
            ('Casa', ['5078313b-5f7d-4e2a-a974-e658237cbd44', 'm']),
            ('Theya', ['I verify the ownership of the vault key.', "m/48'/0'/0'/2'/0/0", 'p2wpkh']),
            ('Theya', ['I verify the ownership of the vault key.', "m/48h/1h/0h/2h"]),
        )
        for service, lines in accepted:
            flow = await validate(lines, False, service)
            assert not MockErrorPage.errors, (service, lines, MockErrorPage.errors)
            assert flow.next_state == flow.sign_health_check

        # Any other key is refused, whichever service asks, including the
        # single-signature keys of the wallet itself.
        not_allowed = 'Health check derivation path is not allowed.'
        refused_paths = (
            (None, 'm/49/0/1/0/0'),
            ('Casa', path),
            ('Casa', "m/44'/0'/0'/0/0"),
            ('Casa', "m/49'/0'/0'/0/0"),
            ('Casa', 'm/49/0'),
            ('Casa', 'm/49/2/1/0/0'),
            ('Casa', 'm/49/0/1/2/0'),
            ('Casa', "m/49/0/1/0/0'"),
            ('Casa', 'm/49/0/1/0/0/0'),
            ('Casa', "m/48'/0'/0'/2'/0/0"),
            ('Theya', path),
            ('Theya', 'm'),
            ('Theya', 'm/49/0/1/0/0'),
            ('Theya', "m/48'/0'/0'/3'/0/0"),
            ('Theya', "m/48'/0/0'/2'/0/0"),
            ('Theya', "m/48'/0'/0'/2'/2/0"),
        )
        for service, refused_path in refused_paths:
            assert_refused(await validate(['hello', refused_path], False, service), not_allowed)

        # Taproot signatures are not part of either health check.
        assert_refused(await validate(['hello', "m/48'/0'/0'/2'/0/0", 'p2tr'], False, 'Theya'),
                       'Health check address type is not supported.')

        # Health checks only use the 2- or 3-line format, so an Electrum-format
        # file is read as that, and a single line is not a health check at all.
        assert_refused(await validate(['signmessage m/49/0/1/0/0 ascii:hello'], False, 'Casa'),
                       'Health check format is invalid.')
        assert_refused(await validate(('signmessage m/49/0/1/0/0 ascii:line\nbreak').splitlines(), False, 'Casa'))

        # Strict text checks also apply to health checks, deliberately.
        for message in (' leading', 'trailing ', 'four    spaces', 'a\x00b', '\u00e9'):
            assert_refused(await validate([message, 'm/49/0/1/0/0'], False, 'Casa'))

        return_value.write(b'OK')
    finally:
        pages.ErrorPage = original_error_page


asyncio.run(run_tests())
