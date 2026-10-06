# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

import uasyncio as asyncio
import flows.scv_flow as scv_module
from data_codecs.ur2_codec import UR2Decoder
from foundation import ur


class MockScanFlow:
    result = None

    def __init__(self, **kwargs):
        assert kwargs['ur_types'] == [ur.Value.PASSPORT_REQUEST]

    async def run(self):
        return self.result


class MockFlow:
    envoy = True
    prompt_skip = 'skip'
    next_state = None
    error = None

    def goto(self, state):
        self.next_state = state

    async def show_error(self, message):
        self.error = message


async def run_tests():
    original_scan = scv_module.ScanQRFlow
    scv_module.ScanQRFlow = MockScanFlow
    try:
        request_cbor = b'\xa2\x01\xd8\x25\x50' + bytes(16) + b'\x03\xd9\x02\xd0\xf5'
        ur.encoder_start(ur.new_raw('crypto-request', request_cbor), 535)
        decoder = UR2Decoder()
        decoder.add_data(ur.encoder_next_part())
        assert decoder.is_complete()
        MockScanFlow.result = decoder.decode()
        flow = MockFlow()
        await scv_module.ScvFlow.scan_qr_challenge(flow)
        assert flow.error == 'Security Check QR code is invalid.'
        assert flow.next_state is None

        MockScanFlow.result = None
        flow = MockFlow()
        await scv_module.ScvFlow.scan_qr_challenge(flow)
        assert flow.error is None
        assert flow.next_state == 'skip'
        return_value.write(b'OK')
    finally:
        scv_module.ScanQRFlow = original_scan


asyncio.run(run_tests())
