# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# export_multisig_qr_flow.py - Export a multisig wallet via QR code

from flows import Flow


class ExportMultisigQRFlow(Flow):
    def __init__(self, context=None):
        from multisig_wallet import MultisigWallet
        super().__init__(initial_state=self.scan_qr_code, name='ExportMultisigQRFlow')

        self.storage_idx = context
        self.ms = MultisigWallet.get_by_idx(self.storage_idx)

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
            if e.args is None or len(e.args) == 0:
                self.error = "Multisig Import Error"
            else:
                self.error = e.args[0]
            self.goto(self.show_error)
            return
        # print('New MS: {}'.format(self.ms.serialize()))

        self.goto(self.do_import)

    async def do_import(self):
        from flows import ImportMultisigWalletFlow
        from pages import SuccessPage

        # Show the wallet to the user for import
        result = await ImportMultisigWalletFlow(self.ms).run()
        if result:
            await SuccessPage(text='Multisig config imported').show()
        self.set_result(result)

    async def show_error(self):
        from pages import ErrorPage
        await ErrorPage(text=self.error).show()
        self.error = None
        self.reset(self.scan_qr_code)
