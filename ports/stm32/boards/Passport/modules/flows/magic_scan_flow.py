# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# magic_scan_flow.py - Scan a QR code and "magically" figure out which handler flow to run.

from flows.flow import Flow


class MagicScanFlow(Flow):
    def __init__(self, flow=None, card_header=None, statusbar=None):
        super().__init__(initial_state=self.scan_qr, name='MagicScanFlow')
        self.flow = flow
        self.card_header = card_header
        self.statusbar = statusbar

    async def scan_qr(self):
        import microns
        from pages.scan_qr_page import ScanQRPage
        from data_codecs.data_format import get_flow_for_data

        result = await ScanQRPage(
            card_header=self.card_header, statusbar=self.statusbar, right_micron=microns.Checkmark)
        if result is None:
            # User canceled the scan
            self.set_result(False)
        else:
            # Got a scan result (aka QRScanResult): good data or error
            if result.error is not None:
                from pages.error_page import ErrorPage

                # Unable to scan QR code - show error?
                await ErrorPage(text='Unable to scan QR code.'.show())
                self.set_result(False)
            else:
                data = result.data
                if flow is None:
                    flow = get_flow_for_data(data)
                flow_result = await flow(data).run()
                # We ran the flow whether it was successful or not.
                # Caller usually won't care though.
                self.set_result(flow_result)
