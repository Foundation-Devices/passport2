# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# sign_psbt_qr_flow.py - Sign a PSBT from a microSD card

from flows import Flow, ScanQRFlow
from data_codecs.qr_type import QRType
from foundation import FixedBytesIO, ur
from passport import mem
from pages import ErrorPage


class SignPsbtQRFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.scan_transaction, name='SignPsbtQRFlow')
        self.raw_psbt = None
        self.ur_type = None
        self.psbt = None

    async def scan_transaction(self):
        result = await ScanQRFlow(qr_types=[QRType.QR, QRType.UR2],
                                  ur_types=[ur.Value.CRYPTO_PSBT, ur.Value.BYTES],
                                  data_description='a PSBT file').run()
        if result is None:
            # User canceled the scan
            self.set_result(False)
            return

        if isinstance(result, ur.Value):
            self.ur_type = result.ur_type()

            if self.ur_type == ur.Value.CRYPTO_PSBT:
                self.raw_psbt = result.unwrap_crypto_psbt()
            elif self.ur_type == ur.Value.BYTES:
                self.raw_psbt = result.unwrap_bytes()
        else:
            self.raw_psbt = result

        self.goto(self.copy_to_flash)

    async def copy_to_flash(self):
        import gc
        from utils import spinner_task
        from tasks import copy_psbt_to_external_flash_task
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

        self.raw_psbt = None
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

        if self.ur_type is None:
            qr_type = QRType.QR
            qr_data = b2a_hex(signed_bytes)
        else:
            qr_type = QRType.UR2
            if self.ur_type == ur.Value.CRYPTO_PSBT:
                qr_data = ur.new_bytes(signed_bytes)
            elif self.ur_type == ur.Value.BYTES:
                qr_data = ur.new_crypto_psbt(signed_bytes)
            else:
                raise RuntimeError('Unknown UR type: {}'.format(self.ur_type))

        await ShowQRPage(qr_type=qr_type,
                         qr_data=qr_data,
                         right_micron=microns.Checkmark).show()
        self.set_result(True)
