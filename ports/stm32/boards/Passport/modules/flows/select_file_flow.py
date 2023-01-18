# SPDX-FileCopyrightText: 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# select_file_flow.py - Decide what to do with a selected file

from flows import Flow


class SelectFileFlow(Flow):
    def __init__(self, active_path, file_name, full_path, is_folder):
        self.active_path = active_path
        self.file_name = file_name
        self.full_path = full_path
        self.is_folder = is_folder
        self.error = None
        super().__init__(initial_state=self.create, name='SelectFileFlow')

    async def create(self):
        from pages import ChooserPage
        if len(self.file_name) != 0:
            self.goto(self.choose_action)
            return

        options = [{'label': 'File', 'value': False},
                   {'label': 'Folder', 'value': True}]
        self.is_folder = await ChooserPage(options=options).show()

        if self.is_folder is None:
            self.set_result(None)
            return

        self.goto(self.name_file)

    async def name_file(self):
        from pages import TextInputPage
        from utils import create_file
        # TODO: fix error handling of files with '/' in the name
        self.file_name = await TextInputPage(card_header={'title': 'Enter File Name'}).show()
        if self.file_name is None:
            self.set_result(None)
            return

        self.full_path = self.active_path + '/' + self.file_name
        try:
            create_file(self.full_path, self.is_folder)
        except Exception as e:
            if e.args is None or len(e.args) == 0:
                self.error = "File Creation Error"
            else:
                self.error = e.args[0]
            self.goto(self.show_error)
            return
        self.set_result(None)

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
        from pages import QuestionPage
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

    async def show_error(self):
        from pages import ErrorPage
        await ErrorPage(text=self.error).show()
        self.error = None
        self.reset(self.name_file)
