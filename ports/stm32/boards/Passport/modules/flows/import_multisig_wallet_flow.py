# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# import_multisig_wallet_flow.py - Show user details of a wallet to be imported, then save if accepted

from flows import Flow
from pages import LongTextPage, ErrorPage


class ImportMultisigWalletFlow(Flow):
    def __init__(self, ms):
        super().__init__(initial_state=self.show_overview, name='ImportMultisigWalletFlow')
        self.ms = ms

    async def show_overview(self):
        msg, is_dup = self.ms.format_overview()

        if is_dup:
            await ErrorPage(text="Duplicate wallet will not be imported.").show()
            self.set_result(False)
            return
        else:
            result = await LongTextPage(card_header={'title': 'Confirm Import'}, text=msg, centered=True).show()
            if not result:
                self.set_result(False)
                return

        self.goto(self.show_details)

    async def show_details(self):
        from errors import Error
        from utils import spinner_task, escape_text
        from tasks import save_multisig_wallet_task

        msg = self.ms.format_details()

        result = await LongTextPage(card_header={'title': escape_text(self.ms.name)}, text=msg, centered=True).show()
        if not result:
            self.back()
        else:
            # User confirmed the import, so save
            (error,) = await spinner_task('Saving multisig', save_multisig_wallet_task, args=[self.ms])
            if not error:
                self.set_result(True)
            elif error is Error.USER_SETTINGS_FULL:
                await ErrorPage(text='Out of space in user settings. Too many multisig configs?').show()
                self.set_result(False)
            else:
                await ErrorPage(text='Unable to save multisig config.').show()
                self.set_result(False)
