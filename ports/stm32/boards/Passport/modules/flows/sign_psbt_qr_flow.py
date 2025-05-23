# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# sign_psbt_qr_flow.py - Sign a PSBT from a microSD card

from flows import Flow
import gc


class SignPsbtQRFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.scan_transaction, name='SignPsbtQRFlow')
        self.raw_psbt = None
        self.ur_type = None
        self.psbt = None
        self.txid = None
        self.is_comp = None
        self.out2_fn = None
        self.written = False
        self.signed_bytes = None
        self.max_frames = 35
        self.filename = None

    async def scan_transaction(self):
        from foundation import ur
        from data_codecs.qr_type import QRType
        from flows import ScanQRFlow, SignPsbtMicroSDFlow
        from errors import Error
        from pages import YesNoChooserPage, ErrorPage
        import microns
        import passport

        result = await ScanQRFlow(qr_types=[QRType.QR, QRType.UR2],
                                  ur_types=[ur.Value.PSBT, ur.Value.BYTES],
                                  data_description='a PSBT file',
                                  max_frames=self.max_frames,
                                  failure_message="Unable to Scan QR code, \
try signing using the microSD card.\n\n{}").run()
        if result is None:
            # User canceled the scan
            self.set_result(False)
            return

        if result == Error.PSBT_OVERSIZED:
            text = "This transaction is large and will take some time to scan. \
How would you like to proceed?"

            if passport.IS_COLOR:
                text = '\n' + text + '\n'

            result = await YesNoChooserPage(text=text,
                                            yes_text='Continue with QR',
                                            no_text='Sign with microSD',
                                            left_micron=microns.Back).show()

            if result is None or result:
                self.max_frames = None
            else:
                result = await SignPsbtMicroSDFlow().run()
                self.set_result(result)
            return  # Run it again with no max frames if the user wants

        if result == Error.QR_TOO_LARGE:
            await ErrorPage("QR code is too large, please sign with microSD.").show()
            self.set_result(False)
            return

        if isinstance(result, ur.Value):
            self.ur_type = result.ur_type()

            if self.ur_type == ur.Value.PSBT:
                self.raw_psbt = result.unwrap_psbt()
            elif self.ur_type == ur.Value.BYTES:
                self.raw_psbt = result.unwrap_bytes()
        else:
            self.raw_psbt = result

        self.goto(self.copy_to_flash)

    async def copy_to_flash(self):
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
        result = await SignPsbtCommonFlow(self.psbt_len).run()

        gc.collect()

        if result is None:
            self.set_result(False)
        else:
            self.psbt = result
            self.goto(self.get_signed_bytes)

    async def get_signed_bytes(self):
        from foundation import FixedBytesIO
        from pages import ErrorPage
        from passport import mem

        # Copy signed txn into a bytearray and show the data as a UR
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

        self.is_comp = self.psbt.is_complete()
        self.psbt = None
        gc.collect()
        self.goto(self.show_signed_transaction)

    async def show_signed_transaction(self):
        from pages import ShowQRPage, ErrorPage
        from data_codecs.qr_type import QRType
        from ubinascii import hexlify as b2a_hex
        import microns
        from foundation import ur

        gc.collect()

        if self.ur_type is None:
            qr_type = QRType.QR
            qr_data = b2a_hex(self.signed_bytes)
        else:
            qr_type = QRType.UR2
            if self.ur_type == ur.Value.PSBT:
                qr_data = ur.new_psbt(self.signed_bytes)
            elif self.ur_type == ur.Value.BYTES:
                qr_data = ur.new_bytes(self.signed_bytes)
            else:
                raise RuntimeError('Unknown UR type: {}'.format(self.ur_type))

        result = False
        try:
            result = await ShowQRPage(qr_type=qr_type,
                                      qr_data=qr_data,
                                      left_micron=microns.MicroSD,
                                      right_micron=microns.Checkmark).show()
        except MemoryError as e:
            result2 = await ErrorPage(text='Transaction is too complex: {}'.format(e),
                                      left_micron=microns.MicroSD,
                                      right_micron=microns.Cancel).show()
            if not result2:
                self.goto(self.save_to_microsd)
            else:
                self.set_result(False)
            return

        if not result:
            self.goto(self.save_to_microsd)
            return

        self.set_result(True)

    async def save_to_microsd(self):
        from flows import SaveToMicroSDFlow
        from pages import ErrorPage
        from utils import get_folder_path
        from public_constants import DIR_TRANSACTIONS
        from ubinascii import hexlify as b2a_hex
        import microns

        gc.collect()

        # Check that the psbt has been written
        if self.written:
            self.goto(self.show_success)
            return

        base = 'QR'

        if not self.is_comp:
            # Keep the filename under control during multiple passes
            target_fname = base + '-part.psbt'
        else:
            # Add -signed to end. We won't offer to sign again.
            target_fname = base + '-signed.psbt'

        try:
            self.filename = await SaveToMicroSDFlow(filename=target_fname,
                                                    data=b2a_hex(self.signed_bytes),
                                                    success_text="psbt",
                                                    path=get_folder_path(DIR_TRANSACTIONS),
                                                    automatic=False,
                                                    auto_prompt=True).run()
        except MemoryError as e:
            result = await ErrorPage(text='Transaction is too large to switch to microSD. '
                                          'Finish signing via QR or start over with microSD.',
                                     left_micron=microns.ScanQR).show()
            if not result:
                self.goto(self.show_signed_transaction)
                return

            self.set_result(False)
            return

        if self.filename is None:
            self.back()
            return

        self.written = True
        self.goto(self.show_success)

    async def show_success(self):
        import microns
        from lvgl import LARGE_ICON_SUCCESS
        from styles.colors import DEFAULT_LARGE_ICON_COLOR
        from pages import LongTextPage

        msg = "Updated PSBT is:\n\n%s" % self.filename
        result = await LongTextPage(text=msg,
                                    centered=True,
                                    left_micron=microns.ScanQR,
                                    right_micron=microns.Checkmark,
                                    icon=LARGE_ICON_SUCCESS,
                                    icon_color=DEFAULT_LARGE_ICON_COLOR).show()

        if not result:
            self.goto(self.show_signed_transaction)
            return

        self.set_result(True)
