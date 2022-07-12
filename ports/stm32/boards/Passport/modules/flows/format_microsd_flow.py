# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# format_microsd_flow.py - Ask the user to confirm, then format the microsd card

from flows import Flow
from tasks import format_microsd_task, make_microsd_file_system_task
from pages import ProgressPage, QuestionPage, SuccessPage, ErrorPage, InsertMicroSDPage
from utils import spinner_task, start_task
from errors import Error
import pyb


class FormatMicroSDFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.confirm_format, name='FormatMicroSDFlow')
        self.result = None
        self.prev_card_header = None

    async def check_for_microsd(self):
        sd = pyb.SDCard()
        if not sd:
            await ErrorPage(text='Unable to communicate with microSD card controller.')
            self.set_result(False)
            return

        if sd.present():
            self.goto(self.confirm_format)
        else:
            result = await InsertMicroSDPage().show()
            if not result:
                self.set_result(False)

    async def confirm_format(self):
        self.result = await QuestionPage(text='Erase and reformat the microSD card?').show()
        if self.result:
            self.goto(self.do_format)
        else:
            self.set_result(False)

    async def on_done_format(self, error=None):
        self.error = error
        self.progress_page.set_result(error is None)

    async def do_format(self):
        # Could implement something like progress_task() similar to spinner_task() to clean up ProgressPage handling
        self.progress_page = ProgressPage(text='Formatting microSD')

        start_task(format_microsd_task(self.progress_page.set_progress, self.on_done_format))

        result = await self.progress_page.show()
        if result:
            self.goto(self.make_file_system)
        else:  # elif self.error is Error.MICROSD_CARD_MISSING:
            result = await InsertMicroSDPage().show()
            if not result:
                self.set_result(False)

    async def make_file_system(self):
        (error,) = await spinner_task('Creating new file system', make_microsd_file_system_task)
        if error is None:
            await SuccessPage(text='Formatting complete.').show()
            self.set_result(True)
        elif self.error is Error.MICROSD_CARD_MISSING:
            result = await InsertMicroSDPage().show()
            if not result:
                self.set_result(False)
        elif self.error is Error.MICROSD_CARD_MISSING:
            await ErrorPage(text='Unable to complete formatting.').show()
            self.set_result(False)
