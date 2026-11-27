# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

import uasyncio as asyncio
import flows.scv_flow as scv_module
from data_codecs.ur2_codec import UR2Decoder
from foundation import ur
from ubinascii import hexlify, unhexlify


class MockScanFlow:
    result = None

    def __init__(self, **kwargs):
        assert kwargs['ur_types'] == [ur.Value.PASSPORT_REQUEST]

    async def run(self):
        return self.result


class MockFlow:
    envoy = True
    prompt_skip = 'skip'
    show_envoy_scan_msg = 'envoy-response'
    next_state = None
    error = None

    def goto(self, state):
        self.next_state = state

    async def show_error(self, message):
        self.error = message


def decode_request(request_cbor):
    MAX_QR_CHARACTERS = 535
    MAX_SCAN_FRAMES = 10
    ur.encoder_start(ur.new_raw('crypto-request', request_cbor), MAX_QR_CHARACTERS)
    decoder = UR2Decoder()
    for _ in range(MAX_SCAN_FRAMES):
        decoder.add_data(ur.encoder_next_part())
        if decoder.is_complete():
            break
    assert decoder.is_complete()
    return decoder.decode()


async def run_tests():
    uuid = bytes(range(16))
    challenge_id = bytes(range(32))
    signature = bytes(range(64))
    expected_hash = unhexlify('6c86c6aac5fb24bcf5d9939cb7d7d5645ce39418f449e03b262dd4fa14b4b92b')
    response_words = ['alpha', 'bravo', 'charlie', 'delta']
    validation_calls = []

    def verify_signature(challenge_hash, challenge_signature):
        assert challenge_hash == expected_hash
        assert challenge_signature == signature
        validation_calls.append('signature')
        return True

    class MockPinAttempt:
        @staticmethod
        def supply_chain_validation_words(challenge):
            assert challenge == challenge_id
            validation_calls.append('words')
            return response_words

    original_scan = scv_module.ScanQRFlow
    original_verify = scv_module.passport.verify_supply_chain_server_signature
    original_pin_attempt = scv_module.PinAttempt
    scv_module.ScanQRFlow = MockScanFlow
    scv_module.passport.verify_supply_chain_server_signature = verify_signature
    scv_module.PinAttempt = MockPinAttempt
    try:
        request_cbor = b'\xa2\x01\xd8\x25\x50' + bytes(16) + b'\x03\xd9\x02\xd0\xf5'
        MockScanFlow.result = decode_request(request_cbor)
        flow = MockFlow()
        await scv_module.ScvFlow.scan_qr_challenge(flow)
        assert flow.error == 'Security Check QR code is invalid.'
        assert flow.next_state is None

        MockScanFlow.result = None
        flow = MockFlow()
        await scv_module.ScvFlow.scan_qr_challenge(flow)
        assert flow.error is None
        assert flow.next_state == 'skip'
        assert validation_calls == []

        request_cbor = (b'\xa2\x01\xd8\x25\x50' + uuid + b'\x02\xd9\x02\xc6\xa2' +
                        b'\x01\x78\x40' + hexlify(challenge_id) + b'\x02\x78\x80' + hexlify(signature))
        MockScanFlow.result = decode_request(request_cbor)
        flow = MockFlow()
        await scv_module.ScvFlow.scan_qr_challenge(flow)
        assert flow.error is None
        assert flow.uuid == uuid
        assert flow.words == response_words
        assert flow.next_state == 'envoy-response'
        assert validation_calls == ['signature', 'words']
        return_value.write(b'OK')
    finally:
        scv_module.ScanQRFlow = original_scan
        scv_module.passport.verify_supply_chain_server_signature = original_verify
        scv_module.PinAttempt = original_pin_attempt


asyncio.run(run_tests())
