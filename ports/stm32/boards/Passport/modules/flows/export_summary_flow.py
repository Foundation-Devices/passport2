# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# export_summary_flow.py - Flow to let export a summary of the current wallet

from files import _try_microsd
from flows import Flow
from pages import SuccessPage, ErrorPage, InsertMicroSDPage, QuestionPage
from tasks import export_summary_task
from utils import spinner_task
from errors import Error


class ExportSummaryFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.confirm_export, name="ListFilesFlow")
        self.error = None

    async def on_done(self, error=None):
        self.error = error
        self.spinner_page.set_result(error is None)

    async def confirm_export(self):
        result = await QuestionPage(text='Export wallet info to microSD?').show()
        if result:
            self.goto(self.do_export)
        else:
            self.set_result(False)

    async def do_export(self):
        # TODO: should this be done similar to "with CardSlot() as Card"
        if not _try_microsd():
            result = await InsertMicroSDPage().show()
            if not result:
                self.set_result(False)
            else:
                return  # Will cause this state to rerun and check the card again

        (error,) = await spinner_task('Exporting wallet summary', export_summary_task, ['public.txt'])
        if error is None:
            await SuccessPage(text='Exported successfully.').show()
            self.set_result(True)
        elif error is Error.MICROSD_CARD_MISSING:
            return
        elif error is Error.FILE_WRITE_ERROR:
            await ErrorPage(text='Unable to export summary file.  Error writing to file.').show()
            self.set_result(False)
