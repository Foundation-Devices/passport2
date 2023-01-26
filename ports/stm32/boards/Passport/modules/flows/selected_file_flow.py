# SPDX-FileCopyrightText: 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# select_file_flow.py - Decide what to do with a selected file

from flows import Flow


class SelectedFileFlow(Flow):
    def __init__(self, file_name, full_path, is_folder):
        super().__init__(initial_state=self.choose_action, name='SelectFileFlow')
        self.file_name = file_name
        self.full_path = full_path
        self.is_folder = is_folder

    async def choose_action(self):
        from pages import ChooserPage
        options = [{'label': 'Navigate' if self.is_folder else 'Select', 'value': 0},
                   {'label': 'Delete', 'value': 1}]

        selection = await ChooserPage(options=options).show()

        if selection is None:
            self.set_result(None)
            return

        if selection == 1:
            self.goto(self.delete_selected_file)
        else:
            self.set_result((self.file_name, self.full_path, self.is_folder))

    async def delete_selected_file(self):
        from utils import delete_file
        if not self.is_folder:
            delete_file(self.full_path)
        self.set_result(None)
