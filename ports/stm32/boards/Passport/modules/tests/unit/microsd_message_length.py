# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

import flows
import pages
import uio
import uasyncio as asyncio
from flows.health_check_microsd_flow import HealthCheckMicrosdFlow
from flows.health_check_common_flow import HealthCheckCommonFlow
from public_constants import AF_CLASSIC


class MockReadFileFlow:
    data = b''

    def __init__(self, path, binary, read_fn):
        assert binary
        self.read_fn = read_fn

    async def run(self):
        stream = uio.BytesIO(self.data)
        result = self.read_fn(stream)
        assert stream.tell() <= 4097
        return result


class MockErrorPage:
    errors = []

    def __init__(self, text):
        self.errors.append(text)

    async def show(self):
        return True


class MockFlow:
    normal_signing = True
    file_path = 'message.txt'
    common_flow = 'validate'
    show_message = 'review'
    addr_type = AF_CLASSIC

    def __init__(self):
        self.next_state = None
        self.result = 'unset'

    def goto(self, state):
        self.next_state = state

    def set_result(self, result):
        self.result = result


async def run_tests():
    original_reader = flows.ReadFileFlow
    original_error_page = pages.ErrorPage
    try:
        flows.ReadFileFlow = MockReadFileFlow
        pages.ErrorPage = MockErrorPage
        path = "m/84'/0'/0'/0/0"
        for prefix, suffix in (('signmessage ' + path + ' ascii:', ''), ('', '\n' + path + '\np2wpkh')):
            for length in (241, 1024, 4096, 4097, 16384):
                message = 'x' * (length - len(prefix) - len(suffix))
                MockReadFileFlow.data = (prefix + message + suffix).encode()
                MockErrorPage.errors = []
                flow = MockFlow()
                await HealthCheckMicrosdFlow.parse_message(flow)
                if length > 4096:
                    assert MockErrorPage.errors == ['Message file is too long. Max length is 4096 bytes.']
                    assert flow.result is False
                    assert flow.next_state is None
                else:
                    assert flow.next_state == flow.common_flow
                    await HealthCheckCommonFlow.validate_lines(flow)
                    assert not MockErrorPage.errors
                    assert flow.text == message
                    assert flow.next_state == flow.show_message
                    assert flow.result == 'unset'

        for message in ('first\nsecond', '\nfirst\n\nsecond\n', 'first\r\n\r\nsecond\r\n',
                        'first\nsecond\r\nthird\n', 'x' * 1000 + '\nlast\n'):
            MockReadFileFlow.data = ('signmessage ' + path + ' ascii:' + message).encode()
            MockErrorPage.errors = []
            flow = MockFlow()
            await HealthCheckMicrosdFlow.parse_message(flow)
            await HealthCheckCommonFlow.validate_lines(flow)
            assert not MockErrorPage.errors
            assert flow.text.encode() == message.encode()
            assert flow.next_state == flow.show_message
            flow.address = '1BoatSLRHtKNngkdXEeobR76b53LETtpyT'
            flow.signature = 'signature'
            await HealthCheckCommonFlow.format_signature(flow)
            assert flow.result.startswith('-----BEGIN BITCOIN SIGNED MESSAGE-----\n' + message + '\n')
            assert '\n-----BEGIN BITCOIN SIGNATURE-----\n' in flow.result
            assert flow.result.endswith('-----END BITCOIN SIGNATURE-----\n')

        for character in tuple(chr(code) for code in range(32) if code != 10) + ('\x7f',):
            MockReadFileFlow.data = ('signmessage ' + path + ' ascii:visible' + character + 'hidden').encode()
            MockErrorPage.errors = []
            flow = MockFlow()
            await HealthCheckMicrosdFlow.parse_message(flow)
            await HealthCheckCommonFlow.validate_lines(flow)
            assert MockErrorPage.errors
            assert flow.result is None
            assert flow.next_state != flow.show_message

        MockReadFileFlow.data = b'\xff'
        MockErrorPage.errors = []
        flow = MockFlow()
        await HealthCheckMicrosdFlow.parse_message(flow)
        assert MockErrorPage.errors == ['Message file contains invalid text.']
        assert flow.result is False
        assert flow.next_state is None
        return_value.write(b'OK')
    finally:
        flows.ReadFileFlow = original_reader
        pages.ErrorPage = original_error_page


asyncio.run(run_tests())
