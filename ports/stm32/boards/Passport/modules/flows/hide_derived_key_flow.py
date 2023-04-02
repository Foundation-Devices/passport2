# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# hide_derived_key_flow.py - Hide a derived key

from flows import Flow


class HideDerivedKeyFlow(Flow):
    def __init__(self, context=None):
        super().__init__(initial_state=self.confirm_hide, name='HideDerivedKeyFlow')
        self.key = context
        self.hidden = self.key['hidden']

    async def confirm_hide(self):
        from pages import QuestionPage

        result = await QuestionPage(text='{} this key?\n\n{}\n(##{})'
                                         .format('Unhide' if self.hidden else 'Hide',
                                                 self.key['name'],
                                                 self.key['index'])).show()

        if result:
            self.goto(self.do_hide)
        else:
            self.set_result(False)

    async def do_hide(self):
        from tasks import hide_derived_key_task
        from utils import spinner_task
        from pages import SuccessPage
        from flows import AutoBackupFlow
        (error,) = await spinner_task('{} Key'
                                      .format('Unhiding' if self.hidden else 'Hiding'),
                                      hide_derived_key_task,
                                      args=[self.key, not self.hidden])
        if error is None:
            await AutoBackupFlow().run()
            self.set_result(True)
        else:
            self.error = 'Key hiding NOT toggled: {}'.format(error)
            self.goto(self.show_error)

    async def show_error(self):
        from pages import ErrorPage
        await ErrorPage(self.error).show()
        self.set_result(False)
