# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# terms_of_use_flow.py - Show the terms of use and get acceptance from user

from flows.flow import Flow


class TermsOfUseFlow(Flow):
    def __init__(self):
        from common import settings

        super().__init__(initial_state=self.show_terms, name='TermsOfUseFlow')

        self.statusbar = {'title': 'TERMS OF USE', 'icon': 'ICON_INFO'}
        # Skip if already accepted
        if settings.get('terms_ok') == 1:
            self.goto(self.show_status)

    async def show_terms(self):
        from pages.accept_terms_chooser_page import AcceptTermsChooserPage
        from common import settings

        result = await AcceptTermsChooserPage().show()
        if result == 'accept':
            settings.set('terms_ok', 1)
            self.set_result(True)
        else:
            self.goto(self.show_error)

    async def show_status(self):
        from pages.info_page import InfoPage
        import microns

        result = await InfoPage(text="You have already accepted the terms of use.",
                                left_micron=microns.Back, right_micron=microns.Checkmark).show()
        self.set_result(result)

    async def show_error(self):
        from pages.error_page import ErrorPage
        from pages.shutdown_page import ShutdownPage

        # User cannot proceed without accepting the Terms
        result = await ErrorPage(text='You must accept the Terms of Use in order to continue with setup.',
                                 left_micron=microns.Shutdown, right_micron=microns.Retry).show()
        if result:
            self.back()
        else:
            # This will either shutdown or return here and retry
            await ShutdownPage().show()
