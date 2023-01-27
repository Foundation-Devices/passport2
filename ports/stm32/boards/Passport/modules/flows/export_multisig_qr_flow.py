# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# export_multisig_qr_flow.py - Export a multisig wallet via QR code

from flows import Flow


class ExportMultisigQRFlow(Flow):
    def __init__(self, context=None):
        from multisig_wallet import MultisigWallet
        super().__init__(initial_state=self.show_qr_code, name='ExportMultisigQRFlow')

        self.storage_idx = context
        self.ms = MultisigWallet.get_by_idx(self.storage_idx)
        self.ms_text = self.ms.to_file()

    async def show_qr_code(self):
        from pages import ShowQRPage
        from data_codecs.qr_type import QRType
        from multisig_wallet import MultisigWallet

        await ShowQRPage(qr_type=QRType.UR2, qr_data=self.ms_text).show()
        self.set_result(True)
