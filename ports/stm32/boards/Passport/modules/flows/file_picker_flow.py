# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# file_picker_flow.py - Allow the user to pick a file and (optionally) navigate up/down folder hierarchy

import lvgl as lv
from animations.constants import TRANSITION_DIR_POP, TRANSITION_DIR_PUSH
from files import CardMissingError, CardSlot
from flows import Flow, SelectedFileFlow
from pages import FilePickerPage, StatusPage, InsertMicroSDPage
from styles.colors import COPPER
import microns
import common
from utils import get_file_list


def file_key(f):
    (filename, _fullpath, is_folder) = f
    return '{}::{}'.format('0' if is_folder else '1', filename.lower())


class FilePickerFlow(Flow):
    def __init__(
            self,
            initial_path=None,
            show_folders=False,
            enable_parent_nav=False,
            suffix=None,
            filter_fn=None,
            select_text="Select",
            allow_delete=False):
        from files import CardSlot
        from utils import bind, show_card_missing

        if not initial_path:
            initial_path = CardSlot.get_sd_root()

        super().__init__(initial_state=self.show_file_picker,
                         name='FilePickerFlow: {}'.format(initial_path))

        self.initial_path = initial_path
        self.paths = [initial_path]
        self.show_folders = show_folders
        self.enable_parent_nav = enable_parent_nav
        self.suffix = suffix
        self.filter_fn = filter_fn
        self.select_text = select_text
        self.status_page = None
        self.empty_result = None
        self.finished = False
        self.allow_delete = allow_delete

        bind(self, show_card_missing)

    def on_empty_sd_card_change(self, sd_card_present):
        if sd_card_present:
            return True  # This will cause a refresh
        else:
            self.reset_paths()
            self.status_page.set_result(None)
            self.goto(self.show_card_missing)
            return False

    async def on_empty_result(self, res):
        self.empty_result = res
        return True

    def on_exception(self, exception):
        self.handle_fatal_error(exception)
        return True

    def on_file_sd_card_change(self, sd_card_present):
        if not sd_card_present:
            self.reset_paths()
            self.goto(self.show_card_missing)
            return True

    def finalize(self, result):
        common.page_transition_dir = TRANSITION_DIR_POP
        self.set_result(result)
        self.finished = True

    async def on_file_result(self, res):
        # No file selected - go back to previous page
        if res is None:
            common.page_transition_dir = TRANSITION_DIR_POP
            if len(self.paths) <= 1:
                self.set_result(None)
                self.finished = True
            else:
                # Go back up a level
                self.paths.pop(-1)
            return True

        _filename, full_path, is_folder = res
        if is_folder:
            common.page_transition_dir = TRANSITION_DIR_PUSH
            self.paths.append(full_path)
            return True

        if not self.allow_delete:
            self.finalize((_filename, full_path, is_folder))
            return True

        result = await SelectedFileFlow(_filename, full_path, is_folder, self.select_text).run()

        if result is not None:
            self.finalize(result)

        return True

    async def show_file_picker(self):
        from utils import show_page_with_sd_card, get_backups_folder_path, get_folder_path
        from public_constants import DIR_TRANSACTIONS

        while True:
            # Get list of files/folders at the current path
            try:
                active_idx = len(self.paths) - 1
                active_path = self.paths[active_idx]
                files = get_file_list(
                    active_path,
                    include_folders=self.show_folders,
                    include_parent=self.enable_parent_nav,
                    suffix=self.suffix,
                    filter_fn=self.filter_fn)

                reverse = False
                if (active_path == get_backups_folder_path() or
                        active_path == get_folder_path(DIR_TRANSACTIONS)):
                    reverse = True
                files = sorted(files, key=file_key, reverse=reverse)

            except CardMissingError:
                self.reset_paths()
                self.goto(self.show_card_missing)
                return

            is_root = active_path == CardSlot.get_sd_root()
            if is_root:
                title = 'microSD'
                icon = 'ICON_MICROSD'
            else:
                leaf_folder_name = active_path.split('/')[-1]
                title = leaf_folder_name
                icon = 'ICON_FOLDER'

            if len(files) == 0:
                self.status_page = StatusPage(
                    text='No files found',
                    card_header={'title': title, 'icon': icon},
                    icon=lv.LARGE_ICON_ERROR,
                    icon_color=COPPER,
                    left_micron=microns.Back,
                    right_micron=None,  # No retry micron because the SD card contents can't magically change
                )

                await show_page_with_sd_card(self.status_page,
                                             self.on_empty_sd_card_change,
                                             self.on_empty_result,
                                             self.on_exception)

                if self.empty_result is False:
                    # When error message is dismissed, only quit the flow entirely if
                    # there's no way back up to a previous level
                    if len(self.paths) <= 1:
                        self.set_result(None)
                        return
                    else:
                        # Go back up a level and refresh the flow
                        self.paths.pop(-1)
                        continue
            else:
                file_picker_page = FilePickerPage(
                    files=files,
                    card_header={'title': title, 'icon': icon}
                )

                await show_page_with_sd_card(file_picker_page,
                                             self.on_file_sd_card_change,
                                             self.on_file_result,
                                             self.on_exception)

                if self.finished:
                    return

    def reset_paths(self):
        self.paths = [self.initial_path]
