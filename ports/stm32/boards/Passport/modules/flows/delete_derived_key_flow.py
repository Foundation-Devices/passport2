# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# delete_derived_key_flow.py - Delete a derived key

from flows import Flow


class DeleteDerivedKeyFlow(Flow):
    def __init__(self, context=None):
        super().__init__(initial_state=self.confirm_delete, name='ExportMultisigQRFlow')
        self.key = context

    async def confirm_delete(self):
        from pages import QuestionPage

        result = await QuestionPage(text='Delete this key?\n\n{}\n(##{})'.format(
            self.key['name'], self.key['index'])).show()

        if result:
            self.goto(self.do_delete)
        else:
            self.set_result(False)

    async def do_delete(self):
        from tasks import delete_derived_key_task
        from utils import spinner_task
        from pages import SuccessPage
        from flows import AutoBackupFlow
        (error,) = await spinner_task('Deleting Key', delete_derived_key_task,
                                      args=[self.key])
        if error is None:
            await SuccessPage(text='Key Deleted').show()
            await AutoBackupFlow().run()
            self.set_result(True)
        else:
            self.error = 'Key NOT deleted: {}'.format(error)
            self.goto(self.show_error)

    async def show_error(self):
        from pages import ErrorPage
        await ErrorPage(self.error).show()
        self.set_result(False)
