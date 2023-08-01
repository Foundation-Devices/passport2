# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# fcc_test_flow.py - Flow to iterate through a test loop indefinitely

from flows import Flow

_CAMERA_DISPLAY_DURATION_SECS = const(5 * 1000)
_FILE_SIZE_TO_CREATE = const(250 * 1024)


class FCCTestFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.show_camera, name='FccTestFlow')
        self.progress_page = None

    async def show_camera(self):
        from flows import ScanQRFlow

        result = await ScanQRFlow(auto_close_timeout=_CAMERA_DISPLAY_DURATION_SECS,
                                  data_description='a normal QR code').run()

        # User used a button to back out
        if result is None:
            self.set_result(False)
            return

        self.goto(self.copy_files)

    async def copy_files(self):
        from developer.fcc_copy_files_task import fcc_copy_files_task
        import microns
        from pages import ProgressPage
        from utils import start_task
        from files import CardSlot
        from uasyncio import sleep_ms

        self.progress_page = ProgressPage(card_header={'title': 'Copy Files'},
                                          text='Copying files from microSD to flash and back.',
                                          left_micron=microns.Cancel,
                                          right_micron=microns.Cancel)

        copy_files_task = start_task(
            fcc_copy_files_task(CardSlot.get_file_path('fcc-file-copy-test.bin')[0],
                                _FILE_SIZE_TO_CREATE,
                                self.progress_page.set_progress,
                                self.progress_page.set_text,
                                self.on_done))

        result = await self.progress_page.show()
        if result is not None:
            # User used a button to back out, so cancel the task. and return from the page
            copy_files_task.cancel()
            self.set_result(False)
            self.progress_page = None
            return

        # NOTE: This sleep is necessary to avoid starting to animate to the next page
        #       while the previous animation is still active (which causes a crash)
        await sleep_ms(2000)
        self.back()

    async def on_done(self, error):
        import lvgl as lv
        from animations.constants import TRANSITION_DIR_POP
        from styles.colors import COPPER
        import common
        from errors import Error

        # If user backed out, long_text_page will be None, so nothing to do
        if self.progress_page is None:
            return

        common.page_transition_dir = TRANSITION_DIR_POP
        if error is Error.MICROSD_CARD_MISSING:
            self.progress_page.set_icon(lv.LARGE_ICON_MICROSD, color=COPPER)
            self.progress_page.set_text('Please insert microSD card.')
            self.progress_page.set_result(None)
        else:
            self.progress_page.set_progress(100)
            self.progress_page.set_icon(lv.LARGE_ICON_SUCCESS)
            self.progress_page.set_result(None)
