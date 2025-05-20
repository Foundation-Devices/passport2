# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# envoy_setup_flow.py - The main overall flow for Envoy setup - controls the process

import lvgl as lv
from flows import (
    Flow,
    ConnectWalletFlow,
    SetInitialPINFlow,
    UpdateFirmwareFlow,
    InitialSeedSetupFlow,
    ScvFlow,
)
import microns


class EnvoySetupFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.show_envoy_app_url, settings_key='envoy_setup', name='EnvoySetupFlow')
        self.restore()

    # This stage is no longer needed, but older devices may try to access it
    # through their saved onboarding state.
    async def check_if_envoy_installed(self):
        self.goto(self.show_envoy_app_url)

    async def show_envoy_app_url(self):
        from pages import ShowQRPage
        import passport
        from common import system

        hw_version = 1.2 if passport.IS_COLOR else 1
        fw_version = system.get_software_info()[0]
        qr_data = 'https://qr.foundation.xyz/?t={}&v={}'.format(hw_version, fw_version)
        result = await ShowQRPage(
            qr_data=qr_data,
            caption='Scan with your phone\'s camera or on Envoy.\n').show()
        if not result:
            self.set_result(False)
        else:
            self.goto(self.scv_flow)

    async def scv_flow(self):
        result = await ScvFlow(envoy=True).run()
        if result is None or not result:
            # self.set_result(None, forget_state=True)
            self.back()
        elif result:
            self.goto(self.set_initial_pin)

    async def set_initial_pin(self):
        result = await SetInitialPINFlow().run()
        if not result:
            self.back()
        else:
            self.goto(self.update_firmware)

    async def update_firmware(self):
        from pages import ErrorPage, QuestionPage
        import passport

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
            import common

            self.goto(self.setup_seed)

            # Force a save before the reset
            common.settings.save()

            machine.reset()
        else:
            await ErrorPage(text='We recommend updating Passport\'s firmware at your earliest convenience.').show()

        self.goto(self.setup_seed)

    async def setup_seed(self):
        # Guards to ensure we can't get into a weird state
        if not self.ensure_pin_set():
            return
        await self.ensure_logged_in()

        result = await InitialSeedSetupFlow().run()
        if result is None:
            self.back()
        if not result:
            # No going back() from here
            pass
        else:
            self.goto(self.connect_with_envoy_intro)

    async def connect_with_envoy_intro(self):
        from pages import InfoPage
        from utils import has_seed

        # Can't connect if we don't have a seed yet!
        if not has_seed():
            self.goto(self.show_success)
            return

        # Guards to ensure we can't get into a weird state
        if not self.ensure_pin_set():
            return
        await self.ensure_logged_in()

        result = await InfoPage(
            statusbar={'title': 'CONNECT', 'icon': 'ICON_CONNECT'},
            text='Now, let\'s connect Passport with Envoy.',
            left_micron=None).show()
        self.goto(self.connect_with_envoy)

    async def connect_with_envoy(self):
        import common
        from constants import DEFAULT_ACCOUNT_ENTRY
        from utils import has_seed

        # Guards to ensure we can't get into a weird state
        if not self.ensure_pin_set():
            return
        await self.ensure_logged_in()

        # Can't connect if we don't have a seed yet!
        if not has_seed():
            self.goto(self.show_success)
            return

        # Guards to ensure we can't get into a weird state
        if not self.ensure_pin_set():
            return
        await self.ensure_logged_in()

        # Set default account as active as ConnectWalletFlow needs it
        common.ui.set_active_account(DEFAULT_ACCOUNT_ENTRY)

        result = await ConnectWalletFlow(
            sw_wallet='Envoy',
            statusbar={'title': 'CONNECT', 'icon': 'ICON_CONNECT'}
        ).run()
        if result:
            self.goto(self.show_success)
        else:
            from pages import InfoPage
            await InfoPage(text='You can connect Passport with Envoy or another wallet at a later time.').show()
            common.settings.set('terms_ok', 1)
            self.set_result(True, forget_state=True)

    async def show_success(self):
        from pages import SuccessPage
        import common

        await SuccessPage(text='Passport configured successfully. You can now start using your device.').show()
        common.settings.set('terms_ok', 1)
        self.set_result(True, forget_state=True)

    async def ensure_logged_in(self):
        from utils import is_logged_in
        from pages import InfoPage
        from flows import LoginFlow

        if not is_logged_in():
            await LoginFlow().run()

    async def ensure_pin_set(self):
        from common import pa
        if pa.is_blank():
            self.reset(self.set_initial_pin)
            return False
        return True
