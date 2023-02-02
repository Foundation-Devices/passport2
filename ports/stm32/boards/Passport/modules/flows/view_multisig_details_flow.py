# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# view_multisig_details_flow.py - Show user details of an existing wallet

from flows import Flow
from pages import LongTextPage


class ViewMultisigDetailsFlow(Flow):
    def __init__(self, context=None):
        super().__init__(initial_state=self.show_overview, name='ViewMultisigDetailsFlow')

        from multisig_wallet import MultisigWallet

        self.storage_idx = context
        self.ms = MultisigWallet.get_by_idx(self.storage_idx)

    async def show_overview(self):
        msg, _ = self.ms.format_overview(importing=False)

        result = await LongTextPage(card_header={'title': self.ms.name}, text=msg, centered=True).show()
        if not result:
            self.set_result(False)
            return

        self.goto(self.show_details)

    async def show_details(self):
        msg = self.ms.format_details()

        result = await LongTextPage(card_header={'title': self.ms.name}, text=msg, centered=True).show()
        if not result:
            self.back()
        else:
            self.set_result(True)
