# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# update_firmware_flow.py - Flow to update firmware on Passport

import lvgl as lv
from files import CardSlot
from constants import FW_HEADER_SIZE, FW_MAX_SIZE
import machine
from pages import ErrorPage, ProgressPage, QuestionPage, SuccessPage, InsertMicroSDPage
from tasks import copy_firmware_to_spi_flash_task
from flows import Flow, FilePickerFlow
from utils import read_user_firmware_pubkey, is_all_zero, start_task
from errors import Error


class UpdateFirmwareFlow(Flow):
    def __init__(self, reset_after=True, statusbar=None):
        super().__init__(initial_state=self.choose_file, name='UpdateFirmwareFlow')
        self.update_file_path = None
        self.size = 0
        self.version = None
        self.error = None
        self.reset_after = reset_after
        self.statusbar = statusbar
        self.filename = None

    async def on_done(self, error=None):
        self.error = error
        self.progress_page.set_result(error is None)

    async def choose_file(self):
        root_path = CardSlot.get_sd_root()

        result = await FilePickerFlow(initial_path=root_path,
                                      suffix='-passport.bin',
                                      show_folders=True).run()
        if result is None:
            self.set_result(False)
            return

        self.filename, full_path, is_folder = result
        if not is_folder:
            self.update_file_path = full_path
            self.goto(self.show_firmware_details)

    async def show_firmware_details(self):
        import common
        with CardSlot() as card:
            with open(self.update_file_path, 'rb') as fp:
                import os

                s = os.stat(self.update_file_path)
                self.size = s[6]

                if self.size < FW_HEADER_SIZE:
                    await ErrorPage(text='Firmware file is too small.').show()
                    self.set_result(False)
                    return

                if self.size > FW_MAX_SIZE:
                    await ErrorPage(text='Firmware file is too large.').show()
                    self.set_result(False)
                    return

                # Read the header
                header = fp.read(FW_HEADER_SIZE)
                if len(header) != FW_HEADER_SIZE:
                    await ErrorPage(text='Firmware file is too small, and the system misreported its size.').show()
                    self.set_result(False)
                    return

                # Validate the header
                is_valid, version, error_msg, is_user_signed = common.system.validate_firmware_header(header)
                # print('is_valid={}, version={}, error_msg={}, is_user_signed={}'.format(
                #     is_valid, version, error_msg, is_user_signed))
                self.version = version
                if not is_valid:
                    await ErrorPage(text='Firmware header is invalid.\n\n{}'.format(error_msg)).show()
                    self.set_result(False)
                    return

                if is_user_signed:
                    pubkey_result, pubkey = read_user_firmware_pubkey()
                    if not pubkey_result or is_all_zero(pubkey):
                        await ErrorPage(
                            text='You must install a Developer PubKey before loading custom firmware.').show()
                        self.set_result(False)
                        return

                    result = await ErrorPage(
                        text='This firmware is signed by a custom Developer PubKey.'.format(version)).show()

                result = await QuestionPage(text='Install this firmware update?\n\nVersion:\n{}'.format(version)).show()
                if result:
                    self.goto(self.copy_to_flash)
                else:
                    self.set_result(False)

    async def copy_to_flash(self):
        from common import settings, system, ui

        self.progress_page = ProgressPage(text='Preparing Update', left_micron=None, right_micron=None)

        self.update_task = start_task(copy_firmware_to_spi_flash_task(
            self.update_file_path, self.size, self.progress_page.set_progress, self.on_done))

        prev_top_level = ui.set_is_top_level(False)
        result = await self.progress_page.show()
        if result:
            # Update copied to flash, now we need to store a setting to indicate what from->to version
            # we are updating, then reboot
            (curr_version, _, _, _, _) = system.get_software_info()
            settings.set('update', '{}->{}'.format(curr_version, self.version))  # old_version->new_version
            settings.set('firmware_title', self.filename)
            settings.save()

            if self.reset_after:
                restart_page = SuccessPage(text='Restarting...', right_micron=None)

                def on_restart_timer(t):
                    machine.reset()

                lv.timer_create(on_restart_timer, 1000, None)

                await restart_page.show()
            else:
                ui.set_is_top_level(prev_top_level)
                self.set_result(True)

        elif self.error is Error.MICROSD_CARD_MISSING:
            ui.set_is_top_level(prev_top_level)
            result = await InsertMicroSDPage().show()
            if not result:
                self.back()
            # else we loop around to top of copy_to_flash() again and retry
