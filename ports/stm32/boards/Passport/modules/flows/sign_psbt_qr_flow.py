# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# sign_psbt_qr_flow.py - Sign a PSBT from a microSD card

from flows import Flow
from foundation import FixedBytesIO, ur
from passport import mem
from pages import ErrorPage


class SignPsbtQRFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.scan_transaction, name='SignPsbtQRFlow')
        self.psbt = None
        self.ur_type = None

    async def scan_transaction(self):
        from pages import ScanQRPage, ErrorPage
        import microns

        # TODO: May need to set statusbar content here and restore it after
        result = await ScanQRPage(right_micron=microns.Checkmark).show()
        if result is None:
            # User canceled the scan
            self.set_result(False)
        else:
            # Got a scan result (aka QRScanResult).
            if result.is_failure():
                # Unable to scan QR code - show error?
                await ErrorPage(text='Unable to scan QR code.\n\n{}'.format(result.error)).show()
                self.set_result(False)
            else:
                # TODO: handle hex not only UR. Wasn't handled before the UR
                # rework too.
                if isinstance(result.data, ur.Value):
                    self.qr_type = result.qr_type
                    self.ur_type = result.data.ur_type()

                    if self.ur_type == ur.Value.BYTES:
                        self.raw_psbt = result.data.unwrap_bytes()
                    elif self.ur_type == ur.Value.CRYPTO_PSBT:
                        self.raw_psbt = result.data.unwrap_crypto_psbt()
                    else:
                        await ErrorPage(text='The QR code does not contain a transaction.').show()
                        self.set_result(False)
                        return

                    self.goto(self.copy_to_flash)
                else:
                    await ErrorPage(text='The QR code does not contain a transaction.').show()
                    self.set_result(False)

    async def copy_to_flash(self):
        import gc
        from utils import spinner_task
        from tasks import copy_psbt_to_external_flash_task
        from pages import ErrorPage
        from public_constants import TXN_INPUT_OFFSET
        from errors import Error

        gc.collect()  # Try to avoid excessive fragmentation

        # TODO: Pass on_progress function as the first argument if we want progress or remove it
        (self.psbt_len, self.output_encoder, error) = await spinner_task(
            'Parsing transaction', copy_psbt_to_external_flash_task, args=[None, self.raw_psbt, TXN_INPUT_OFFSET])
        if error is not None:
            if error == Error.PSBT_TOO_LARGE:
                await ErrorPage(text='PSBT too large').show()
            else:
                await ErrorPage(text='Invalid PSBT (copying QR)').show()
            self.set_result(False)
            return

        gc.collect()  # Try to avoid excessive fragmentation

        # PSBT was copied to external flash
        self.goto(self.common_flow)

    async def common_flow(self):
        from flows import SignPsbtCommonFlow

        # This flow validates and signs if all goes well, and returns the signed psbt
        self.psbt = await SignPsbtCommonFlow(self.psbt_len).run()

        if self.psbt is None:
            self.set_result(False)
        else:
            self.goto(self.show_signed_transaction)

    async def show_signed_transaction(self):
        import gc
        from pages import ShowQRPage
        from data_codecs.qr_type import QRType
        from ubinascii import hexlify as b2a_hex
        import microns

        # Copy signed txn into a bytearray and show the data as a UR
        # try:
        signed_bytes = None
        try:
            with FixedBytesIO(mem.psbt_output) as bfd:
                with self.output_encoder(bfd) as fd:
                    # Always serialize back to PSBT for QR codes
                    self.psbt.serialize(fd)
                    bfd.seek(0)
                    signed_bytes = bfd.getvalue()
                    # print('len(signed_bytes)={}'.format(len(signed_bytes)))
                    # print('signed_bytes={}'.format(signed_bytes))
        except MemoryError as e:
            await ErrorPage(text='Transaction is too complex: {}'.format(e)).show()
            self.set_result(False)
            return

        self.psbt = None
        gc.collect()

        if self.qr_type == QRType.QR:
            qr_data = b2a_hex(signed_bytes)
        elif self.qr_type == QRType.UR2 and self.ur_type == ur.Value.BYTES:
            qr_data = ur.new_bytes(signed_bytes)
        elif self.qr_type == QRType.UR2 and self.ur_type == ur.Value.CRYPTO_PSBT:
            qr_data = ur.new_crypto_psbt(signed_bytes)
        else:
            raise RuntimeException("Unsupported output format")

        await ShowQRPage(qr_type=self.qr_type,
                         qr_data=qr_data,
                         right_micron=microns.Checkmark).show()
        self.set_result(True)
