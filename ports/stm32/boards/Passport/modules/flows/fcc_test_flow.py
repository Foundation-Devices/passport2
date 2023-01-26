# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# fcc_test_flow.py - Flow to iterate through a test loop indefinitely

from animations.constants import TRANSITION_DIR_POP
import lvgl as lv
from flows import Flow
import microns
from pages import ScanQRPage, LongTextPage
from styles.colors import COPPER
from tasks import fcc_copy_files_task
from utils import start_task
from files import CardSlot
import common
from uasyncio import sleep_ms
from errors import Error

_CAMERA_DISPLAY_DURATION_SECS = const(5 * 1000)
_FILE_SIZE_TO_CREATE = const(250 * 1024)


class FCCTestFlow(Flow):
    def __init__(self):
        self.long_text_page = None
        super().__init__(initial_state=self.show_camera, name='FccTestFlow')

    async def show_camera(self):
        result = await ScanQRPage().show(auto_close_timeout=_CAMERA_DISPLAY_DURATION_SECS)
        if result is None:
            # User used a button to back out
            self.set_result(False)
            return

        self.goto(self.copy_files)

    async def copy_files(self):
        self.long_text_page = LongTextPage(
            card_header=('title': 'Copy Files'},
            text='Copying files from microSD to flash and back.',
            show_progress=True,
            left_micron=microns.Cancel,
            right_micron=microns.Cancel)

        self.copy_files_task = start_task(
            fcc_copy_files_task(
                CardSlot.get_file_path('fcc-file-copy-test.bin')[0],
                file_size=_FILE_SIZE_TO_CREATE,
                set_progress=self.long_text_page.set_progress,
                set_message=self.long_text_page.set_message,
                on_done=self.on_done))

        result = await self.long_text_page.show()
        if result is not None:
            # User used a button to back out, so cancel the task and return from the page
            self.copy_files_task.cancel()
            self.set_result(False)
            self.long_text_page = None
            return

        # NOTE: This sleep is necessary to avoid starting to animate to the next page
        #       while the previous animation is still active (which causes a crash)
        await sleep_ms(2000)
        self.back()

    async def on_done(self, error):
        # If user backed out, long_text_page will be None, so nothing to do
        if self.long_text_page is None:
            return

        common.page_transition_dir = TRANSITION_DIR_POP
        if error is Error.MICROSD_CARD_MISSING:
            self.long_text_page.set_icon(lv.LARGE_ICON_MICROSD, color=COPPER)
            self.long_text_page.set_text('Please insert microSD card.')
            self.long_text_page.set_result(None)
        else:
            self.long_text_page.set_progress(100)
            self.long_text_page.set_icon(lv.LARGE_ICON_SUCCESS)
            self.long_text_page.set_result(None)
