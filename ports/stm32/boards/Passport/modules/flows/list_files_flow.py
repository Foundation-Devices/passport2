# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# list_files_flow.py - Flow to let user view microSD card files and view the SHA256 of the chosen file

from flows import Flow, FilePickerFlow
from pages import SuccessPage, ErrorPage, ProgressPage, InsertMicroSDPage
from tasks import calculate_file_sha256_task
from utils import start_task, get_basename
from errors import Error
import microns


class ListFilesFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.choose_file, name="ListFilesFlow")
        self.error = None
        self.digest = None

    async def on_done(self, digest, error=None):
        self.digest = digest
        self.error = error
        self.progress_page.set_result(error is None)

    async def choose_file(self):
        result = await FilePickerFlow(show_folders=True,
                                      select_text='Info',
                                      allow_delete=True).run()
        if result is None:
            self.set_result(False)
            return

        _filename, full_path, is_folder = result
        if not is_folder:
            self.file_path = full_path
            self.goto(self.show_sha256)

    async def show_sha256(self):
        self.progress_page = ProgressPage(
            'Calculating SHA256...', left_micron=microns.Cancel, right_micron=microns.Checkmark)

        sha256_task = start_task(calculate_file_sha256_task(
            self.file_path, self.progress_page.set_progress, self.on_done))

        result = await self.progress_page.show()
        if self.error is None:
            if self.digest is not None:
                basename = get_basename(self.file_path)
                await SuccessPage(text='{}\n\nSHA256 Digest: \n{}'.format(basename, self.digest)).show()
                self.set_result(True)
            else:
                # User pressed a key to abort the operation
                # print('>>>> ABORT!!!!!!!')
                sha256_task.cancel()
                self.set_result(False)

        elif self.error is not None:
            if self.error == Error.MICROSD_CARD_MISSING:
                await InsertMicroSDPage().show()
                self.back()
            elif self.error == Error.FILE_READ_ERROR:
                basename = get_basename(self.file_path)
                await ErrorPage(text='Unable to read from file: {}'.format(basename)).show()
                self.back()
            else:
                await ErrorPage(text='Unexpected error ').show
                self.set_result(False)

        self.set_result(result)
