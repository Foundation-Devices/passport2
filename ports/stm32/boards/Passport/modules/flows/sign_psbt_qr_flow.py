# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# sign_psbt_qr_flow.py - Sign a PSBT from a microSD card

from flows import Flow


class SignPsbtQRFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.scan_transaction, name='SignPsbtQRFlow')
        self.raw_psbt = None
        self.ur_type = None
        self.psbt = None
        self.txid = None
        self.out_fn = None
        self.signed_bytes = None
        self.max_frames = 35

    async def scan_transaction(self):
        from foundation import ur
        from data_codecs.qr_type import QRType
        from flows import ScanQRFlow, SignPsbtMicroSDFlow
        from errors import Error
        from pages import LongTextPage
        import microns

        text = "\nThis transaction is quite large, and may take some time to scan. \
Would you like to sign with microSD instead?"
        result = await ScanQRFlow(qr_types=[QRType.QR, QRType.UR2],
                                  ur_types=[ur.Value.CRYPTO_PSBT, ur.Value.BYTES],
                                  data_description='a PSBT file',
                                  max_frames=self.max_frames).run()
        if result is None:
            # User canceled the scan
            self.set_result(False)
            return

        if result == Error.PSBT_OVERSIZED:
            text = "\nThis transaction is quite large, and may take some time to scan. \
Would you like to sign with microSD instead?"
            result = await LongTextPage(text=text,
                                        centered=True,
                                        left_micron=microns.Cancel,
                                        right_micron=microns.Checkmark).show()

            if result:
                result = await SignPsbtMicroSDFlow().run()
                self.set_result(result)
            else:
                self.max_frames = None
            return  # Run it again with no max frames if the user wants

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
        from pages import ErrorPage

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
            self.goto(self.get_signed_bytes)

    async def get_signed_bytes(self):
        from foundation import FixedBytesIO
        from pages import ErrorPage
        from passport import mem

        # Copy signed txn into a bytearray and show the data as a UR
        # try:
        try:
            with FixedBytesIO(mem.psbt_output) as bfd:
                with self.output_encoder(bfd) as fd:
                    # Always serialize back to PSBT for QR codes
                    self.psbt.serialize(fd)
                    bfd.seek(0)
                    self.signed_bytes = bfd.getvalue()
                    # print('len(signed_bytes)={}'.format(len(signed_bytes)))
                    # print('signed_bytes={}'.format(signed_bytes))
        except MemoryError as e:
            await ErrorPage(text='Transaction is too complex: {}'.format(e)).show()
            self.set_result(False)
            return

        self.goto(self.show_signed_transaction)

    async def show_signed_transaction(self):
        from pages import ShowQRPage
        from data_codecs.qr_type import QRType
        from ubinascii import hexlify as b2a_hex
        import microns
        from foundation import ur

        if self.ur_type is None:
            qr_type = QRType.QR
            qr_data = b2a_hex(self.signed_bytes)
        else:
            qr_type = QRType.UR2
            if self.ur_type == ur.Value.CRYPTO_PSBT:
                qr_data = ur.new_bytes(self.signed_bytes)
            elif self.ur_type == ur.Value.BYTES:
                qr_data = ur.new_crypto_psbt(self.signed_bytes)
            else:
                raise RuntimeError('Unknown UR type: {}'.format(self.ur_type))

        result = await ShowQRPage(qr_type=qr_type,
                                  qr_data=qr_data,
                                  left_micron=microns.MicroSD,
                                  right_micron=microns.Checkmark).show()

        if not result:
            self.goto(self.save_to_microsd)
            return

        self.set_result(True)

    def write_final_fn(self, filename):
        from utils import HexWriter

        # write psbt to file as hex
        with HexWriter(open(filename, 'w+t')) as fd:
            self.txid = self.psbt.finalize(fd)
        self.out_fn = filename

    async def save_to_microsd(self):
        from flows import SaveToMicroSDFlow
        from utils import get_folder_path
        from public_constants import DIR_TRANSACTIONS

        if self.out_fn is not None:
            self.goto(self.show_success)
            return

        result = await SaveToMicroSDFlow(filename='QR.txn',
                                         write_fn=self.write_final_fn,
                                         success_text="transaction",
                                         path=get_folder_path(DIR_TRANSACTIONS)).run()
        if not result:
            self.back()
            return

        self.goto(self.show_success)

    async def show_success(self):
        import microns
        from lvgl import LARGE_ICON_SUCCESS
        from styles.colors import DEFAULT_LARGE_ICON_COLOR
        from pages import LongTextPage

        msg = 'Finalized transaction (ready for broadcast):\n\n%s' % self.out_fn

        if self.txid:
            msg += '\n\nFinal TXID:\n' + self.txid

        result = await LongTextPage(text=msg,
                                    centered=True,
                                    left_micron=microns.ScanQR,
                                    right_micron=microns.Checkmark,
                                    icon=LARGE_ICON_SUCCESS,
                                    icon_color=DEFAULT_LARGE_ICON_COLOR,).show()

        if not result:
            self.goto(self.show_signed_transaction)
            return

        self.set_result(True)
