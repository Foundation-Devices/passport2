# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# choose_timezone_flow.py - Choose a timezone

from flows import Flow


class ChooseTimezoneFlow(Flow):
    def __init__(self, context=None):
        super().__init__(initial_state=self.enter_timezone, name='ChooseTimezoneFlow')

    async def enter_timezone(self):
        from pages import TextInputPage, SuccessPage, ErrorPage
        from common import settings
        from utils import InputMode
        import microns
        # from flows import AutoBackupFlow

        timezone = settings.get('timezone', None)
        result = await TextInputPage(card_header={'title': 'GMT Offset'},
                                     numeric_only=False,
                                     initial_text='-' if timezone is None else str(timezone),
                                     initial_mode=InputMode.NUMERIC,
                                     max_length=3,
                                     left_micron=microns.Back,
                                     right_micron=microns.Checkmark).show()
        if result is None:
            self.set_result(False)
            return

        try:
            tz = int(result)
        except Exception as e:
            await ErrorPage('Timezone offset must be a number from -12 to 12.').show()
            return

        if tz < -12 or tz > 12:
            await ErrorPage('Timezones range from GMT-12 to GMT+12.').show()
            return

        await SuccessPage(text='Time Zone Saved').show()
        # TODO: auto backup?
        # await AutoBackupFlow().run()
        settings.set('timezone', tz)
        self.set_result(True)
