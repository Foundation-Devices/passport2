# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# import_multisig_wallet_from_qr_flow.py - Import a multisig wallet from a QR code

from flows import Flow


class ImportMultisigWalletFromQRFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.scan_qr_code, name='ImportMultisigWalletFromQRFlow')
        self.ms = None
        self.error = None

    async def scan_qr_code(self):
        from pages import ScanQRPage
        from multisig_wallet import MultisigWallet

        result = await ScanQRPage(decode_cbor_bytes=True).show()
        if result is None or result.error is not None:
            self.set_result(False)
            return

        data = result.data
        if isinstance(data, (bytes, bytearray)):
            data = data.decode('utf-8')

        try:
            self.ms = await MultisigWallet.from_file(data)
        except BaseException as e:
            self.error = e.args[0]
            if self.error is None:
                self.error = "Unknown Error"
            self.goto(self.show_error)
            return
        # print('New MS: {}'.format(self.ms.serialize()))

        self.goto(self.do_import)

    async def do_import(self):
        from flows import ImportMultisigWalletFlow

        # Show the wallet to the user for import
        result = await ImportMultisigWalletFlow(self.ms).run()
        self.set_result(result)

    async def show_error(self):
        from pages import ErrorPage
        await ErrorPage(text=self.error).show()
        self.error = None
        self.reset(self.scan_qr_code)
