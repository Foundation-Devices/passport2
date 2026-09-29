# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# install_dev_pubkey_flow.py - Flow to let the user choose a dev pubkey file and install it

from flows import Flow, FilePickerFlow
from files import CardMissingError, CardSlot
from pages import ErrorPage, QuestionPage, SuccessPage
from pages.insert_microsd_page import InsertMicroSDPage
from utils import (bytes_to_hex_str, clear_cached_pubkey, is_valid_firmware_pubkey,
                   split_to_lines)
import microns


class InstallDevPubkeyFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.choose_file)

    async def choose_file(self):
        root_path = CardSlot.get_sd_root()

        result = await FilePickerFlow(initial_path=root_path, suffix='-pub.bin', show_folders=True).run()
        if result is None:
            self.set_result(False)
            return

        _filename, full_path, is_folder = result
        if not is_folder:
            self.pubkey_file_path = full_path
            self.goto(self.load_dev_pubkey)

    async def load_dev_pubkey(self):
        try:
            with CardSlot() as card:
                with open(self.pubkey_file_path, 'rb') as fd:
                    import os

                    s = os.stat(self.pubkey_file_path)
                    self.size = s[6]

                    if self.size != 88:
                        await ErrorPage(text='The Developer PubKey file must be exactly 88 bytes long.').show()
                        self.set_result(False)
                        return

                    fd.seek(24)  # Skip the header
                    pubkey = fd.read(64)  # Read the pubkey

                    # print('pubkey = {}'.format(bytes_to_hex_str(pubkey)))
        except CardMissingError:
            result = await InsertMicroSDPage().show()
            if not result:
                self.back()
            return

        # A key that is not a point on the curve can never verify a signature, so
        # there is no reason to write one into the secure element.
        if not is_valid_firmware_pubkey(pubkey):
            await ErrorPage(text='This file does not contain a valid Developer PubKey.').show()
            self.set_result(False)
            return

        self.pubkey = pubkey
        self.goto(self.confirm_dev_pubkey)

    async def confirm_dev_pubkey(self):
        from common import system

        # Show what is about to be trusted, in the same form as View Developer PubKey
        confirmed = await QuestionPage(
            text=split_to_lines(bytes_to_hex_str(self.pubkey), 16),
            card_header={'title': 'Install PubKey?'},
            statusbar={'title': 'DEVELOPER'},
            left_micron=microns.Cancel,
            right_micron=microns.Checkmark
        ).show()

        if not confirmed:
            self.set_result(False)
            return

        clear_cached_pubkey()

        result = system.set_user_firmware_pubkey(self.pubkey)
        if result:
            await SuccessPage(text='Successfully Installed!').show()
            self.set_result(True)
        else:
            await ErrorPage(text='Unable to Install.').show()
            self.set_result(False)
