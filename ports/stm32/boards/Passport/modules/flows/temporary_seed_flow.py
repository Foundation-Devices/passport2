# SPDX-FileCopyrightText: © 2024 Foundation Devices, Inc. <hello@foundation.xyz>
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
        from utils import spinner_task, start_task, is_passphrase_active
        from tasks import delay_task
        from pages import SuccessPage, QuestionPage

        if is_passphrase_active():
            text = 'Clear temporary seed? The current passphrase will be removed.'
        else:
            text = 'Clear temporary seed?'

        result = await QuestionPage(text=text).show()

        if not result:
            # Setting result to false exits temporary mode
            self.set_result(True)
            return

        settings.exit_temporary_mode()
        await SuccessPage(text='Temporary seed cleared').show()
        await self.finalize()

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

        (vals, error) = await spinner_task(text='Retrieving key',
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

        await SuccessPage(text='Temporary seed applied').show()
        await self.finalize(child=True)

    async def finalize(self, child=False):
        self.set_result(True)
        ui.full_cards_refresh(go_to_account_0=child, go_to_plus_menu=(not child))
        await self.wait_to_die()
