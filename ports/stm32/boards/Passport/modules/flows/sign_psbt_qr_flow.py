# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# sign_psbt_qr_flow.py - Sign a PSBT from a microSD card

from flows import Flow


class SignPsbtQRFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.scan_transaction, name='SignPsbtQRFlow')
        self.psbt = None

    async def scan_transaction(self):
        from pages import ScanQRPage, ErrorPage
        import microns

        # TODO: May need to set statusbar content here and restore it after
        result = await ScanQRPage(right_micron=microns.Checkmark, decode_cbor_bytes=True).show()
        if result is None:
            # User canceled the scan
            self.set_result(False)
        else:
            # Got a scan result (aka QRScanResult): good data or error
            if result.error is not None:
                # Unable to scan QR code - show error?
                await ErrorPage(text='Unable to scan QR code.'.show())
                self.set_result(False)
            else:
                self.raw_psbt = result.data
                self.qr_type = result.qr_type
                self.goto(self.copy_to_flash)

    async def copy_to_flash(self):
        import gc
        from utils import spinner_task
        from tasks import copy_psbt_to_external_flash_task
        from pages import ErrorPage
        from public_constants import TXN_INPUT_OFFSET

        # TODO: I think this is always a bytes object -- can probably remove this check
        # The data can be a string or may already be a bytes object
        # if isinstance(self.raw_psbt, bytes):
        #     data_buf = self.raw_psbt
        # else:
        #     data_buf = bytes(self.raw_psbt, 'utf-8')

        gc.collect()  # Try to avoid excessive fragmentation

        # TODO: Pass on_progress function as the first argument if we want progress or remove it
        (self.psbt_len, self.output_encoder, error) = await spinner_task(
            'Parsing transaction', copy_psbt_to_external_flash_task, args=[None, self.raw_psbt, TXN_INPUT_OFFSET])
        if error is not None:
            await ErrorPage(text='Invalid PSBT (copying QR)').show()
            self.set_result(False)
            return

        gc.collect()  # Try to avoid excessive fragmentation

        # PSBT was copied to external flash
        self.goto(self.common_flow)

    async def common_flow(self):
        from flows import SignPsbtCommonFlow

        # This flow validates and signs if all goes well, and returns the signed psbt
        result = await SignPsbtCommonFlow(self.psbt_len).run()
        if result is None:
            self.set_result(False)
        else:
            self.psbt = result
            self.goto(self.show_signed_transaction)

    async def show_signed_transaction(self):
        import gc
        from uio import BytesIO
        from pages import ShowQRPage
        from data_codecs.qr_type import QRType
        from ubinascii import hexlify as b2a_hex
        import microns

        # Copy signed txn into a bytearray and show the data as a UR
        signed_bytes = None
        with BytesIO() as bfd:
            with self.output_encoder(bfd) as fd:
                # Always serialize back to PSBT for QR codes
                self.psbt.serialize(fd)
                bfd.seek(0)
                signed_bytes = bfd.read()
                # print('len(signed_bytes)={}'.format(len(signed_bytes)))
                # print('signed_bytes={}'.format(signed_bytes))

        gc.collect()

        signed_hex = b2a_hex(signed_bytes)

        # print('qr_type={}'.format(self.qr_type))
        await ShowQRPage(
            qr_type=self.qr_type,
            qr_data=signed_bytes if self.qr_type == QRType.UR2 else signed_hex,
            # TODO: This shouldn't be hard-coded
            qr_args={'prefix': 'crypto-psbt'},
            right_micron=microns.Checkmark).show()
        self.set_result(True)
