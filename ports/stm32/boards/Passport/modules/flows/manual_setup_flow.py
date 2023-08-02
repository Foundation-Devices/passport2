# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# manual_setup_flow.py - The main overall flow for manual setup - controls the process

from flows.flow import Flow


class ManualSetupFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.show_intro, settings_key='manual_setup', name='ManualSetupFlow')
        self.restore()

    async def show_intro(self):
        from pages.info_page import InfoPage
        import microns

        result = await InfoPage(text='Manual setup is for advanced users who do not wish to use Envoy.',
                                left_micron=microns.Back).show()
        if not result:
            self.set_result(False)
        else:
            self.goto(self.show_setup_guide_url)

    async def show_setup_guide_url(self):
        from pages.show_qr_page import ShowQRPage

        result = await ShowQRPage(
            qr_data='https://foundationdevices.com/setup',
            caption='To open the online setup guide, scan this QR code with your phone.').show()
        if not result:
            self.back()
        else:
            self.goto(self.show_terms_of_use_flow)

    async def show_terms_of_use_flow(self):
        from flows import TermsOfUseFlow

        result = await TermsOfUseFlow().run()
        if not result:
            self.back()
        else:
            self.goto(self.show_scv)

    async def show_scv(self):
        from flows import ScvFlow

        result = await ScvFlow(envoy=False).run()
        if not result:
            self.back()
        else:
            self.goto(self.set_initial_pin)

    async def set_initial_pin(self):
        from flows import SetInitialPINFlow

        result = await SetInitialPINFlow().run()
        if not result:
            self.back()
        else:
            self.goto(self.update_firmware)

    async def update_firmware(self):
        from pages.error_page import ErrorPage
        from pages.question_page import QuestionPage
        import passport
        import lvgl as lv
        from flows import UpdateFirmwareFlow

        # Guards to ensure we can't get into a weird state
        if not self.ensure_pin_set():
            return
        await self.ensure_logged_in()

        # Intro page
        title = 'UPDATE' + (' FIRMWARE' if passport.IS_COLOR else '')
        result = await QuestionPage(
            icon=lv.LARGE_ICON_FIRMWARE,
            text='Do you want to update Passport\'s firmware now?',
            statusbar={'title': title, 'icon': 'ICON_FIRMWARE'}).show()
        if not result:
            await ErrorPage(text='We recommend updating Passport\'s firmware at your earliest convenience.').show()
            self.goto(self.setup_seed)
            return

        result = await UpdateFirmwareFlow(
            reset_after=False,
            statusbar={'title': title, 'icon': 'ICON_FIRMWARE'}
        ).run()
        if result:
            import machine
            from common import settings

            self.goto(self.setup_seed)

            # Force a save before the reset
            settings.save()

            machine.reset()
        else:
            await ErrorPage(text='We recommend updating Passport\'s firmware at your earliest convenience.').show()

        self.goto(self.setup_seed)

    async def setup_seed(self):
        from flows import InitialSeedSetupFlow

        # Guards to ensure we can't get into a weird state
        if not self.ensure_pin_set():
            return
        await self.ensure_logged_in()

        result = await InitialSeedSetupFlow(is_envoy=False).run()
        if result is None:
            self.back()
        elif not result:
            pass
        else:
            self.goto(self.show_success)

    async def show_success(self):
        from pages.success_page import SuccessPage

        await SuccessPage(text='Passport configured successfully. You can now start using your device.').show()
        self.set_result(True, forget_state=True)

    async def ensure_logged_in(self):
        from utils import is_logged_in
        from pages.info_page import InfoPage
        from flows import LoginFlow

        if not is_logged_in():
            await LoginFlow().run()

    async def ensure_pin_set(self):
        from common import pa
        if pa.is_blank():
            self.reset(self.set_initial_pin)
            return False
        return True
