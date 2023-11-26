# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# sign_psbt_qr_flow.py - Sign a PSBT from a microSD card

from flows import Flow


class SignPsbtFlow(Flow):
    def __init__(self, qr_mode=True):
        initial_state = self.scan_transaction if qr_mode else self.choose_file
        super().__init__(initial_state=initial_state, name='SignPsbtQRFlow')
        self.qr_mode = qr_mode
        self.raw_psbt = None
        self.ur_type = None
        self.psbt = None
        self.txid = None
        self.is_comp = None
        self.out2_fn = None
        self.written = False
        self.signed_bytes = None
        self.max_frames = 35
        self.file_path = None
        self.filename = None
        self.psbt_len = None
        self.output_encoder = None

    async def choose_file(self):
        from flows import FilePickerFlow

        result = await FilePickerFlow(show_folders=True, suffix='psbt', filter_fn=None).run()
        if result is None:
            self.set_result(False)
            return

        _filename, full_path, is_folder = result
        if not is_folder:
            self.file_path = full_path
            self.goto(self.copy_file_to_flash)

    async def copy_file_to_flash(self):
        import gc
        from utils import spinner_task
        from pages import ErrorPage
        from public_constants import TXN_INPUT_OFFSET
        from tasks import copy_psbt_file_to_external_flash_task
        from errors import Error

        # TODO: I think this is always a bytes object -- can probably remove this check
        # The data can be a string or may already be a bytes object
        # if isinstance(self.raw_psbt, bytes):
        #     data_buf = self.raw_psbt
        # else:
        #     data_buf = bytes(self.raw_psbt, 'utf-8')

        gc.collect()  # Try to avoid excessive fragmentation

        # TODO: Pass on_progress function as the first argument if we want progress or remove it
        (self.psbt_len, self.output_encoder, error) = await spinner_task(
            'Parsing transaction',
            copy_psbt_file_to_external_flash_task,
            args=[None, self.file_path, TXN_INPUT_OFFSET])
        if error is not None:
            if error == Error.PSBT_TOO_LARGE:
                await ErrorPage(text='PSBT too large').show()
            else:
                await ErrorPage(text='Invalid PSBT (copying microSD)').show()
            self.set_result(False)
            return

        gc.collect()  # Try to avoid excessive fragmentation

        # PSBT was copied to external flash
        self.goto(self.common_flow)

    async def scan_transaction(self):
        from foundation import ur
        from data_codecs.qr_type import QRType
        from flows import ScanQRFlow, SignPsbtMicroSDFlow
        from errors import Error
        from pages import YesNoChooserPage, ErrorPage
        import microns
        import passport

        result = await ScanQRFlow(qr_types=[QRType.QR, QRType.UR2],
                                  ur_types=[ur.Value.CRYPTO_PSBT, ur.Value.BYTES],
                                  data_description='a PSBT file',
                                  max_frames=self.max_frames,
                                  failure_message="Unable to Scan QR code, \
try signing using the microSD card.\n\n{}",
                                  pass_error=True).run()
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
            await ErrorPage("This transaction is too large for QR signing. \
\nSpend fewer coins or sign via microSD card.").show()

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

        if result is None:
            self.set_result(False)
        else:
            self.psbt = result
            self.goto(self.get_signed_bytes)

    async def get_signed_bytes(self):
        import gc
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
        next_state = self.show_signed_transaction if self.qr_mode else self.save_to_microsd
        self.goto(next_state)

    async def show_signed_transaction(self):
        from pages import ShowQRPage, ErrorPage
        from data_codecs.qr_type import QRType
        from ubinascii import hexlify as b2a_hex
        import microns
        from foundation import ur

        if not self.qr_mode:
            qr_type = QRType.UR2
            qr_data = ur.new_crypto_psbt(self.signed_bytes)
        elif self.ur_type is None:
            qr_type = QRType.QR
            qr_data = b2a_hex(self.signed_bytes)
        else:
            qr_type = QRType.UR2
            if self.ur_type == ur.Value.CRYPTO_PSBT:
                qr_data = ur.new_crypto_psbt(self.signed_bytes)
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

        # Check that the psbt has been written
        if self.written:
            self.goto(self.show_success)
            return

        target_fname = None
        base = None

        if self.qr_mode:
            base = 'QR'
        else:
            orig_path, basename = self.file_path.rsplit('/', 1)
            base = basename.rsplit('.', 1)[0]

        if not self.is_comp:
            # Keep the filename under control during multiple passes
            target_fname = base.replace('-part', '') + '-part.psbt'
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
            await ErrorPage(text='Transaction is too complex: {}'.format(e)).show()
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
