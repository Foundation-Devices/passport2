# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# developer_functions_flow.py - Run a named developer function

from flows import Flow


class DeveloperFunctionsFlow(Flow):
    def __init__(self, fn_name=None):
        super().__init__(initial_state=self.run_function, name='DeveloperFunctionsFlow')
        self.fn_name = fn_name
        print('DeveloperFunctionsFlow: fn_name={}'.format(self.fn_name))

    async def run_function(self):
        if self.fn_name == 'dump_settings':
            from common import settings
            from utils import to_str
            print('Current Settings:\n{}'.format(to_str(settings.current)))
            self.set_result(True)

        elif self.fn_name == 'factory_reset':
            from flows import ResetPINFlow
            from tasks import erase_passport_task
            from utils import spinner_task
            from pages import ErrorPage
            import common
            from common import system

            print('Factory Reset!')

            result = await ResetPINFlow().run()
            if result:
                await spinner_task('Factory Reset Passport...', erase_passport_task, args=[True])
                common.settings.remove('setup_mode')
                system.reset()

                self.set_result(True)
            else:
                await ErrorPage(text='Unable to reset PIN, so not erasing Passport.').show()
                self.set_result(False)
