# SPDX-FileCopyrightText: 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# select_file_flow.py - Decide what to do with a selected file

from flows import Flow
from pages import ChooserPage, QuestionPage


class SelectFileFlow(Flow):
    def __init__(self, file_name, full_path, is_folder):
        self.file_name = file_name
        self.full_path = full_path
        self.is_folder = is_folder
        super().__init__(initial_state=self.choose_action, name='SelectFileFlow')

    async def choose_action(self):
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
        from tasks import delete_directory_task
        from utils import get_file_list, delete_file, spinner_task
        if not self.is_folder:
            delete_file(self.full_path)
            self.set_result(None)
            return

        subfiles = get_file_list(path=self.full_path, include_folders=True)
        if len(subfiles) == 0:
            delete_file(self.full_path)
            self.set_result(None)
            return

        confirm = await QuestionPage(text="Delete folder and all its files?").show()
        if confirm:
            await spinner_task(text="Deleting folder and all its files.",
                               task=delete_directory_task, args=[self.full_path])
        self.set_result(None)
