# SPDX-FileCopyrightText: © 2024 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# temporary_seed_flow.py - Start using a temporary seed

from flows import Flow


class TemporarySeedFlow(Flow):
    def __init__(self, context=None, clear=False):
        self.key = context
        print("context: {}".format(context))
        self.pk = None
        initial_state = self.enter_seed
        if self.key is not None:
            initial_state = self.use_child_seed
        elif clear:
            initial_state = self.clear_seed
        super().__init__(initial_state=initial_state, name='TemporarySeedFlow')

    async def enter_seed(self):
        from flows import InitialSeedSetupFlow
        result = await InitialSeedSetupFlow(temporary=True).run()
        self.set_result(result)

    async def clear_seed(self):
        from utils import spinner_task, start_task
        from tasks import delay_task
        from common import settings, ui
        from pages import SuccessPage

        await spinner_task('Clearing Temporary Seed', delay_task, args=[1000, False])
        settings.exit_temporary_mode()
        await SuccessPage(text='Temporary seed cleared').show()

        # TODO: ui is still buggy when clearing a seed
        ui.full_cards_refresh()
        await self.wait_to_die()
        self.set_result(False)

    async def use_child_seed(self):
        from derived_key import get_key_type_from_tn
        from utils import spinner_task
        from pages import ErrorPage
        from flows import InitialSeedSetupFlow

        self.key_type = get_key_type_from_tn(self.key['tn'])

        if not self.key_type:
            await ErrorPage("Invalid key type number: {}".format(self.key['tn'])).show()
            self.set_result(False)
            return

        (vals, error) = await spinner_task(text='Generating key',
                                           task=self.key_type['task'],
                                           args=[self.key['index']])
        self.pk = vals['priv']
        if error is not None:
            await ErrorPage(error).show()
            self.set_result(False)
            return

        result = await InitialSeedSetupFlow(temporary=True, external_key=self.pk).run()
        self.set_result(result)
