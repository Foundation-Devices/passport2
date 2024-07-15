# SPDX-FileCopyrightText: © 2024 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# temporary_seed_flow.py - Start using a temporary seed

from flows import Flow
from common import settings, ui


class TemporarySeedFlow(Flow):
    def __init__(self, context=None, clear=False):
        self.key = context
        initial_state = self.enter_seed
        if clear:
            initial_state = self.clear_seed
        elif self.key is not None:
            initial_state = self.use_child_seed
        super().__init__(initial_state=initial_state, name='TemporarySeedFlow')

    # Override set_result to safely exit temporary mode
    def set_result(self, result, forget_state=True):
        if not result:
            settings.exit_temporary_mode()
        super().set_result(result, forget_state)

    async def enter_seed(self):
        from flows import RestoreSeedFlow

        settings.enter_temporary_mode()
        result = await RestoreSeedFlow(refresh_cards_when_done=True,
                                       autobackup=False,
                                       full_backup=True,
                                       temporary=True).run()
        self.set_result(result)

    async def clear_seed(self):
        from utils import spinner_task, start_task
        from tasks import delay_task
        from pages import SuccessPage

        settings.exit_temporary_mode()
        # await spinner_task('Clearing temporary seed', delay_task, args=[1000, False])
        await SuccessPage(text='Temporary seed cleared').show()

        self.set_result(True)
        ui.full_cards_refresh()
        await self.wait_to_die()

    async def use_child_seed(self):
        from derived_key import get_key_type_from_tn
        from utils import spinner_task
        from tasks import save_seed_task
        from pages import ErrorPage, SuccessPage, InfoPage
        import microns

        result = await InfoPage('{} will be used as a temporary seed'.format(self.key['name']),
                                left_micron=microns.Back).show()

        if not result:
            self.set_result(False)
            return

        self.key_type = get_key_type_from_tn(self.key['tn'])

        if not self.key_type:
            await ErrorPage("Invalid key type number: {}".format(self.key['tn'])).show()
            self.set_result(False)
            return

        (vals, error) = await spinner_task(text='Generating key',
                                           task=self.key_type['task'],
                                           args=[self.key['index']])
        pk = vals['priv']
        if error is not None:
            await ErrorPage(error).show()
            self.set_result(False)
            return

        settings.enter_temporary_mode()
        (error,) = await spinner_task('Applying seed', save_seed_task, args=[pk])

        if error is not None:
            self.set_result(None)
            return

        await SuccessPage(text='Temporary seed applied.').show()

        self.set_result(True)
        ui.full_cards_refresh()
        await self.wait_to_die()
