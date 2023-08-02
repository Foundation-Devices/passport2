# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# rename_multisig_flow.py - Rename a multisig entry

from flows.flow import Flow


class RenameMultisigFlow(Flow):
    def __init__(self, context=None):
        from multisig_wallet import MultisigWallet

        self.storage_idx = context
        self.error = None
        self.new_name = None

        self.ms = MultisigWallet.get_by_idx(self.storage_idx)

        if self.ms is not None:
            initial_state = self.ask_for_name
        else:
            self.error = 'No multisig config!'
            initial_state = self.show_error

        super().__init__(initial_state=initial_state, name='RenameMultisigFlow')

    async def ask_for_name(self):
        from constants import MAX_MULTISIG_NAME_LEN
        from pages.text_input_page import TextInputPage
        import microns

        name = self.ms.name if self.new_name is None else self.new_name
        result = await TextInputPage(title='New Multisig Name',
                                     initial_text=name,
                                     max_length=MAX_MULTISIG_NAME_LEN,
                                     left_micron=microns.Cancel,
                                     right_micron=microns.Checkmark).show()
        if result is not None:
            self.new_name = result

            # TODO: I think we allowed multiple with the same name in Gen 1
            # # Check for existing multisig with this name
            # existing_account = get_account_by_name(self.new_name)
            # if existing_account is not None:
            #     await ErrorPage(text='Account #{} already exists with the name "{}".'.format(
            #         existing_account.get('acct_num'), self.new_name)).show()
            #     return

            self.goto(self.do_rename)
        else:
            self.set_result(False)

    async def do_rename(self):
        import lvgl as lv
        from common import keypad
        from tasks import rename_multisig_task
        from utils import spinner_task
        from pages.error_page import ErrorPage
        from pages.success_page import SuccessPage
        import passport

        (error,) = await spinner_task('Renaming multisig', rename_multisig_task,
                                      args=[self.ms, self.new_name])
        if error is None:
            from flows import AutoBackupFlow

            await SuccessPage(text='Multisig config renamed').show()

            await AutoBackupFlow().run()

            self.set_result(True)

            # TODO: is it necessary to back out of the menu here?

        else:
            await ErrorPage(text='Multisig config NOT renamed: {}'.format(self.error)).show()
            self.set_result(False)

    async def show_error(self):
        from pages.error_page import ErrorPage

        await ErrorPage(self.error).show()
        self.set_result(False)
