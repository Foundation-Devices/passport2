# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# insert_microsd_page.py

from pages.status_page import StatusPage
import microns


class InsertMicroSDPage(StatusPage):
    def __init__(self, text=None, card_header={'title': 'No microSD'},
                 statusbar=None, left_micron=microns.Back, right_micron=microns.Retry):
        import lvgl as lv
        from styles.colors import DEFAULT_LARGE_ICON_COLOR

        if text is None:
            text = 'Please insert a\nmicroSD card.'

        super().__init__(
            text=text,
            icon=lv.LARGE_ICON_MICROSD,
            icon_color=DEFAULT_LARGE_ICON_COLOR,
            card_header=card_header,
            statusbar=statusbar,
            left_micron=left_micron,
            right_micron=right_micron)

    async def show(self):
        from utils import show_page_with_sd_card

        result = False

        def on_sd_card_change(sd_card_present):
            # Treat SD card being inserted as success.
            nonlocal result
            if sd_card_present:
                result = True

            return sd_card_present

        async def on_result(res):
            nonlocal result
            result = res
            return True

        def on_exception(exception):
            self.handle_fatal_error(exception)
            return True

        await show_page_with_sd_card(self, on_sd_card_change, on_result, on_exception)

        return result
