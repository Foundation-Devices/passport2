# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
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
            await ErrorPage(text="Duplicate multisig wallet will not be imported.").show()
            self.set_result(False)
            return

        await LongTextPage(card_header={'title': 'Confirm Import'}, text=msg, centered=True, left_micron=None).show()

        self.goto(self.show_details)

    async def show_details(self):
        from utils import escape_text

        msg = self.ms.format_details()

        result = await LongTextPage(card_header={'title': escape_text(self.ms.name)}, text=msg, centered=True).show()

        if not result:
            self.back()
            return

        self.goto(self.confirm_import)

    async def confirm_import(self):
        from pages import QuestionPage

        result = await QuestionPage('Import new multisig wallet?').show()

        if not result:
            self.set_result(False)
            return

        self.goto(self.import_wallet)

    async def import_wallet(self):
        from utils import spinner_task
        from errors import Error
        from tasks import save_multisig_wallet_task

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
