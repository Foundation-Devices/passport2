# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# display_transaction_flow.py - Display a transaction in another format

from flows import Flow


class DisplayTransactionFlow(Flow):
    def __init__(self, qr_mode=False):
        initial_state = self.scan_transaction if qr_mode else self.choose_file
        super().__init__(initial_state=initial_state, name='DisplayTransactionFlow')
        self.qr_mode = qr_mode
        self.ur_type = None
        self.written = False
        self.signed_bytes = None
        self.max_frames = 35
        self.filename = None
        self.data = None

    async def choose_file(self):
        from flows import FilePickerFlow, ReadFileFlow
        from pages import ErrorPage

        result = await FilePickerFlow(show_folders=True, suffix='psbt', filter_fn=None).run()

        if result is None:
            self.set_result(False)
            return

        _filename, full_path, is_folder = result
        self.data = await ReadFileFlow(full_path, binary=True).run()

        if self.data is None:
            await ErrorPage('No data found in file').show()
            self.set_result(False)
            return

        self.goto(self.display_transaction)

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
                                  failure_message="Unable to Scan QR code, \
try signing using the microSD card.\n\n{}",
                                  pass_error=True).run()
        if result is None:
            # User canceled the scan
            self.set_result(False)
            return

        if isinstance(result, ur.Value):
            self.ur_type = result.ur_type()

            if self.ur_type == ur.Value.CRYPTO_PSBT:
                self.data = result.unwrap_crypto_psbt()
            elif self.ur_type == ur.Value.BYTES:
                self.data = result.unwrap_bytes()
        else:
            self.data = result

        self.goto(self.save_to_microsd)

    async def display_transaction(self):
        from pages import ShowQRPage, ErrorPage
        from data_codecs.qr_type import QRType
        from ubinascii import hexlify as b2a_hex
        import microns
        from foundation import ur

        qr_type = QRType.UR2
        qr_data = ur.new_crypto_psbt(self.data)

        try:
            await ShowQRPage(qr_type=qr_type,
                             qr_data=qr_data,
                             right_micron=microns.Checkmark).show()
        except MemoryError as e:
            await ErrorPage(text='Transaction is too complex: {}'.format(e),
                            right_micron=microns.Cancel).show()

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

        base = 'QR'
        path = get_folder_path(DIR_TRANSACTIONS)

        # Add -signed to end. We won't offer to sign again.
        target_fname = base + '-signed.psbt'

        try:
            self.filename = await SaveToMicroSDFlow(filename=target_fname,
                                                    data=b2a_hex(self.data),
                                                    success_text="psbt",
                                                    path=path,
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
                                    right_micron=microns.Checkmark,
                                    icon=LARGE_ICON_SUCCESS,
                                    icon_color=DEFAULT_LARGE_ICON_COLOR).show()

        self.set_result(True)
