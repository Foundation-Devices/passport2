# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# delete_deriveds_key_flow.py - Delete derived keys

from flows.flow import Flow


class DeleteDerivedKeysFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.confirm_delete, name='DeleteDerivedKeysFlow')

    async def confirm_delete(self):
        from pages.question_page import QuestionPage

        result = await QuestionPage(text='Delete all Child Keys?').show()

        if result:
            self.goto(self.do_delete)
        else:
            self.set_result(False)

    async def do_delete(self):
        from common import settings
        from pages.success_page import SuccessPage

        settings.remove('derived_keys')
        settings.save()
        await SuccessPage(text='Keys Deleted').show()
        self.set_result(True)
