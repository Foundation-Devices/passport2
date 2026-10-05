# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

import uasyncio as asyncio
import flows.scan_qr_flow as scan_module
import flows.connect_wallet_flow as connect_module
from foundation import ur
from data_codecs.ur2_codec import UR2Decoder
from pages.scan_qr_page import QRScanResult
from wallets.multisig_import import read_multisig_config_from_qr


class MockPage:
    result = None
    messages = []

    def __init__(self, **kwargs):
        if 'text' in kwargs:
            self.messages.append(kwargs['text'])

    async def show(self, **kwargs):
        return self.result


class MockInfoPage(MockPage):
    result = True


class MockConnectFlow:
    sw_wallet = {'label': 'test wallet'}
    do_multisig_config_import = 'import'

    def __init__(self):
        self.sig_type = {'import_qr': read_multisig_config_from_qr}
        self.multisig_import_data = None
        self.next_state = None
        self.result = None

    def get_custom_text(self, key, default):
        return default

    def goto(self, state):
        self.next_state = state

    def set_result(self, result):
        self.result = result


async def import_result(result):
    MockPage.result = result
    MockPage.messages = []
    flow = MockConnectFlow()
    await connect_module.ConnectWalletFlow.import_multisig_config_from_qr(flow)
    return flow


async def run_tests():
    original_scan = scan_module.ScanQRPage
    original_error = scan_module.ErrorPage
    original_long_error = scan_module.LongErrorPage
    original_info = connect_module.InfoPage
    original_connect_error = connect_module.ErrorPage
    scan_module.ScanQRPage = MockPage
    scan_module.ErrorPage = MockPage
    scan_module.LongErrorPage = MockPage
    connect_module.InfoPage = MockInfoPage
    connect_module.ErrorPage = MockPage
    try:
        config = 'Name: Test wallet\nPolicy: 2 of 3\n'
        for data in (config, ur.new_bytes(config.encode())):
            flow = await import_result(QRScanResult(data=data))
            assert flow.multisig_import_data == config
            assert flow.next_state == 'import'
            assert len(MockPage.messages) == 1

        # A model request exercises the UUID-bearing union variant from the report.
        request_cbor = b'\xa2\x01\xd8\x25\x50' + bytes(16) + b'\x03\xd9\x02\xd0\xf5'
        ur.encoder_start(ur.new_raw('crypto-request', request_cbor), 535)
        decoder = UR2Decoder()
        decoder.add_data(ur.encoder_next_part())
        assert decoder.is_complete()
        request = decoder.decode()
        assert request.ur_type() == ur.Value.PASSPORT_REQUEST
        for wrong_type in (ur.new_psbt(b'not a multisig configuration'), request):
            try:
                wrong_type.unwrap_bytes()
            except ValueError:
                pass
            else:
                raise AssertionError('wrong UR tag accepted by unwrap_bytes')

            flow = await import_result(QRScanResult(data=wrong_type))
            assert flow.next_state is None
            assert flow.multisig_import_data is None
            assert 'This type of UR is not expected' in MockPage.messages[-1]

        flow = await import_result(None)
        assert flow.next_state is None
        assert flow.multisig_import_data is None
        assert len(MockPage.messages) == 1

        flow = await import_result(QRScanResult(data=ur.new_bytes(b'\xff')))
        assert flow.next_state is None
        assert 'Unexpected data format' in MockPage.messages[-1]

        flow = await import_result(QRScanResult(error=ur.TooBigError()))
        assert flow.next_state is None
        assert flow.result is False

        flow = await import_result(QRScanResult(error=ValueError('invalid QR')))
        assert flow.next_state is None
        assert 'Unable to scan QR code' in MockPage.messages[-1]
    finally:
        scan_module.ScanQRPage = original_scan
        scan_module.ErrorPage = original_error
        scan_module.LongErrorPage = original_long_error
        connect_module.InfoPage = original_info
        connect_module.ErrorPage = original_connect_error


asyncio.run(run_tests())
return_value.write(b'OK')
