# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# delete_multisig_flow.py - Delete the specified multisig config

from flows.flow import Flow


class DeleteMultisigFlow(Flow):
    def __init__(self, context):
        from multisig_wallet import MultisigWallet

        self.storage_idx = context
        self.error = None

        self.ms = MultisigWallet.get_by_idx(self.storage_idx)

        if self.ms is not None:
            initial_state = self.confirm_delete
        else:
            self.error = 'No multisig config!'
            initial_state = self.show_error

        super().__init__(initial_state=initial_state, name='DeleteMultisigFlow')

    async def confirm_delete(self):
        from pages.question_page import QuestionPage
        result = await QuestionPage(text='Are you sure you to delete want this multisig config?\n\n{}'.format(
            self.ms.name)).show()
        if result:
            self.goto(self.do_delete)
        else:
            self.set_result(False)

    async def do_delete(self):
        import lvgl as lv
        from common import keypad
        from tasks import delete_multisig_task
        from pages.success_page import SuccessPage
        from utils import spinner_task
        import passport

        (error,) = await spinner_task('Deleting multisig', delete_multisig_task,
                                      args=[self.ms])
        if error is None:
            from flows import AutoBackupFlow

            await SuccessPage(text='Multisig config deleted').show()

            await AutoBackupFlow().run()

            self.set_result(True)

        else:
            self.error = 'Multisig config NOT deleted: {}'.format(error)
            self.goto(self.show_error)

    async def show_error(self):
        from pages.error_page import ErrorPage
        await ErrorPage(self.error).show()
        self.set_result(False)
