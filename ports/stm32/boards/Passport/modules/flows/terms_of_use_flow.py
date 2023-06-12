# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# terms_of_use_flow.py - Show the terms of use and get acceptance from user

import lvgl as lv
from flows import Flow
import microns
import common


class TermsOfUseFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.show_terms, name='TermsOfUseFlow')

        self.statusbar = {'title': 'TERMS OF USE', 'icon': 'ICON_INFO'}
        # Skip if already accepted
        if common.settings.get('terms_ok') == 1:
            self.goto(self.show_status)

    async def show_terms(self):
        from pages import AcceptTermsChooserPage

        result = await AcceptTermsChooserPage().show()
        if result == 'accept':
            common.settings.set('terms_ok', 1)
            self.set_result(True)
        else:
            self.goto(self.show_error)

    async def show_status(self):
        from pages import InfoPage
        result = await InfoPage(text="You have already accepted the terms of use.",
                                left_micron=microns.Back, right_micron=microns.Checkmark).show()
        self.set_result(result)

    async def show_error(self):
        from pages import ErrorPage, ShutdownPage

        # User cannot proceed without accepting the Terms
        result = await ErrorPage(text='You must accept the Terms of Use in order to continue with setup.',
                                 left_micron=microns.Shutdown, right_micron=microns.Retry).show()
        if result:
            self.back()
        else:
            # This will either shutdown or return here and retry
            await ShutdownPage().show()
