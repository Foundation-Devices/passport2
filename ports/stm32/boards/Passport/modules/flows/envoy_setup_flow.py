# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
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
        super().__init__(initial_state=self.check_if_envoy_installed, settings_key='envoy_setup', name='EnvoySetupFlow')
        self.restore()

    # Open Envoy and select "Setup a New Passport"

    async def check_if_envoy_installed(self):
        from pages import ChooserPage
        from utils import recolor
        from styles.colors import HIGHLIGHT_TEXT_HEX

        options = [{'label': 'Continue on Envoy', 'value': True},
                   {'label': 'Download Envoy App', 'value': False}]

        is_envoy_installed = await ChooserPage(
            text='In Envoy, select:\n{}'.format(recolor(HIGHLIGHT_TEXT_HEX, 'Set up a new Passport')),
            options=options,
            icon=lv.LARGE_ICON_INFO,
            left_micron=microns.Back,
            initial_value=options[0].get('value')).show()
        if is_envoy_installed is None:
            self.set_result(False)
        elif is_envoy_installed:
            self.goto(self.scv_flow)
        else:
            self.goto(self.show_envoy_app_url)

    async def show_envoy_app_url(self):
        from pages import ShowQRPage

        result = await ShowQRPage(
            qr_data='https://foundationdevices.com/download',
            caption='Scan from your phone to download Envoy.\n').show()
        if not result:
            self.back()
        else:
            self.goto(self.scv_flow)

    async def scv_flow(self):
        result = await ScvFlow(envoy=True).run()
        if result is None:
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

        # Guards to ensure we can't get into a weird state
        if not self.ensure_pin_set():
            return
        await self.ensure_logged_in()

        # Intro page
        result = await QuestionPage(
            icon=lv.LARGE_ICON_FIRMWARE,
            text='Do you want to update Passport\'s firmware now?',
            statusbar={'title': 'UPDATE FIRMWARE', 'icon': lv.ICON_FIRMWARE}).show()
        if not result:
            await ErrorPage(text='We recommend updating Passport\'s firmware at your earliest convenience.').show()
            self.goto(self.setup_seed)
            return

        result = await UpdateFirmwareFlow(
            reset_after=False,
            statusbar={'title': 'UPDATE FIRMWARE', 'icon': lv.ICON_FIRMWARE}
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
            statusbar={'title': 'CONNECT', 'icon': lv.ICON_CONNECT},
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
            statusbar={'title': 'CONNECT', 'icon': lv.ICON_CONNECT}
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
