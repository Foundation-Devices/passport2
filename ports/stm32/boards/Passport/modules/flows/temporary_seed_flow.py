# SPDX-FileCopyrightText: © 2024 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# temporary_seed_flow.py - Start using a temporary seed

from flows import Flow


class TemporarySeedFlow(Flow):
    def __init__(self, clear=False):
        initial_state = self.enter_seed if not clear else self.clear_seed
        super().__init__(initial_state=initial_state, name='TemporarySeedFlow')

    async def enter_seed(self):
        from flows import InitialSeedSetupFlow
        result = await InitialSeedSetupFlow(temporary=True).run()
        self.set_result(result)

    async def clear_seed(self):
        from utils import spinner_task
        from tasks import delay_task
        from common import settings
        from pages import SuccessPage

        await spinner_task('Clearing Temporary Seed', delay_task, args=[1000, False])
        await SuccessPage(text='Temporary seed cleared').show()
        settings.exit_temporary_mode()
        self.set_result(True)
