# SPDX-FileCopyrightText: © 2024 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# temporary_seed_flow.py - Start using a temporary seed

from flows import Flow
from common import settings


class TemporarySeedFlow(Flow):
    def __init__(self, context=None, initial=False):
        import stash

        # Caller wants to set this passphrase
        self.key = context
        self.pk = None
        self.attempted = False
        self.initial = initial
        initial_state = self.clear_seed
        if initial:
            initial_state = self.enter_seed
        if context is not None:
            initial_state = self.set_seed
        super().__init__(initial_state=initial_state, name='TemporarySeedFlow')

    def clean(self):
        import stash

        settings.set_volatile('temporary_mode', False)
        settings.set_volatile('temporary_seed', None)
        with stash.SensitiveValues() as sv:
            sv.capture_xpub()

    async def enter_seed(self):
        from flows import InitialSeedSetupFlow

        settings.set_volatile('temporary_mode', True)

        result = await InitialSeedSetupFlow(temporary=True).run()

        if not result:
            self.clean()
            if self.attempted:
                self.goto(self.confirm_xfp)
            else:
                self.set_result(False)
            return

        self.goto(self.confirm_xfp)

    async def set_seed(self):
        from utils import get_derived_key_from_data, spinner_task
        from tasks import save_seed_task
        from pages import ErrorPage

        if self.attempted:
            self.clean()
            self.key = None
            self.goto(self.confirm_xfp)
            return

        result, _, self.pk = await get_derived_key_from_data(self.key)

        if not result:
            self.set_result(False)
            return

        settings.set_volatile('temporary_mode', True)
        (error,) = await spinner_task('Saving temporary seed', save_seed_task, args=[self.pk])

        if error is not None:
            await ErrorPage('Unable to save temporary seed.').show()
            self.clean()
            self.set_result(False)
            return

        self.goto(self.confirm_xfp)

    async def clear_seed(self):
        from pages import QuestionPage
        import stash

        result = await QuestionPage(text='Clear the temporary seed?').show()

        if not result:
            self.set_result(False)
            return

        self.clean()
        self.goto(self.confirm_xfp)

    async def confirm_xfp(self):
        from utils import start_task, xfp2str
        from pages import QuestionPage, SuccessPage
        from common import ui

        # Make a success page
        if self.key is None and not self.initial:
            await SuccessPage(
                text='Temporary seed removed.\n\nFingerprint:\n\n{}'.format(
                    xfp2str(settings.get('xfp', '---')))
            ).show()
        else:
            self.attempted = True
            result = await QuestionPage(
                text='Temporary seed entered.\n\nFingerprint correct?\n\n{}'.format(
                    xfp2str(settings.get('xfp', '---')))
            ).show()

            if result is False:
                settings.set('temporary_seed', None)
                self.back()
                return

        ui.update_cards(stay_on_last_card=True)

        async def start_main_task():
            ui.start_card_task(card_idx=ui.active_card_idx)

        start_task(start_main_task())

        await self.wait_to_die()

        self.set_result(True)
