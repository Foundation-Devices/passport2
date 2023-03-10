# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
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
        from data_codecs.qr_type import QRType
        from foundation import ur
        from flows import ScanQRFlow
        from multisig_wallet import MultisigWallet

        result = await ScanQRFlow(qr_types=[QRType.UR2],
                                  ur_types=[ur.Value.BYTES],
                                  data_description='a multisig wallet configuration file').run()
        if result is None:
            self.set_result(False)
            return

        try:
            file = result.unwrap_bytes().decode('utf-8')
            self.ms = await MultisigWallet.from_file(file)
        except BaseException as e:
            if e.args is None or len(e.args) == 0:
                self.error = "Multisig Import Error"
            else:
                self.error = e.args[0]
            self.goto(self.show_error)
            return

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
