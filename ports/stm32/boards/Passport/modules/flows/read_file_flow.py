# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# read_file_flow.py - Read a file and handle errors

from flows import Flow


class ReadFileFlow(Flow):
    def __init__(self, file_path, binary=True, automatic=False, read_fn=None):
        from utils import bind, show_card_missing

        self.file_path = file_path
        self.binary = binary
        self.read_fn = read_fn

        # Used in flow_show_card_missing
        self.automatic = automatic

        bind(self, show_card_missing)

        super().__init__(initial_state=self.read_file,
                         name='ReadFileFlow')

    async def read_file(self):
        from utils import spinner_task
        from tasks import read_file_task
        from errors import Error
        from pages import ErrorPage

        (data, error) = await spinner_task('Reading file',
                                           read_file_task,
                                           args=[self.file_path, self.binary, self.read_fn])

        if error is Error.MICROSD_CARD_MISSING:
            self.goto(self.show_card_missing)
            return

        if error is Error.FILE_READ_ERROR:
            if not self.automatic:
                await ErrorPage('Unable to read file from microSD card.').show()
            self.set_result(None)
            return

        if len(data) == 0:
            if not self.automatic:
                await ErrorPage('File is empty.').show()
            self.set_result(None)
            return

        self.set_result(data)
