# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# insert_microsd_page.py

import lvgl as lv
from pages import StatusPage
from styles.colors import FD_BLUE
import microns
from files import CardMissingError, CardSlot
from uasyncio import sleep_ms


class InsertMicroSDPage(StatusPage):
    # Used to back up a previous SD card callback if any
    prev_sd_card_cb = None

    # SD card interrupt event
    sd_card_change = False

    def __init__(self, text=None, card_header={'title': 'No microSD'},
                 statusbar=None, left_micron=microns.Back, right_micron=microns.Retry):
        if text is None:
            text = 'Please insert a\nmicroSD card.'

        super().__init__(
            text=text,
            icon=lv.LARGE_ICON_MICROSD,
            icon_color=FD_BLUE,
            card_header=card_header,
            statusbar=statusbar,
            left_micron=left_micron,
            right_micron=right_micron)

    async def show(self):
        # Activate SD card hook
        self.prev_sd_card_cb = CardSlot.get_sd_card_change_cb()
        CardSlot.set_sd_card_change_cb(self.handle_sd_card_cb)

        self.display()

        # Poll the user input alongside SD card interrupt flag
        g = self.poll_for_done()
        while True:
            try:
                next(g)
                await sleep_ms(10)

                # SD card just got inserted or removed
                if self.sd_card_change:
                    self.sd_card_change = False

                    try:
                        with CardSlot():
                            # Restore previous SD card callback
                            self.restore_sd_cb()

                            # Restore statusbar and card header
                            self.restore_statusbar_and_card_header()

                            return True
                    except CardMissingError:
                        pass

            except StopIteration as result:
                self.restore_statusbar_and_card_header()
                self.restore_sd_cb()

                return result.value
            except Exception as e:
                self.restore_sd_cb()
                self.handle_fatal_error(e)

    def handle_sd_card_cb(self):
        if self.sd_card_change:
            return

        self.sd_card_change = True

    def restore_sd_cb(self):
        CardSlot.set_sd_card_change_cb(self.prev_sd_card_cb)
