# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# install_dev_pubkey_flow.py - Flow to let the user choose a dev pubkey file and install it

from flows.flow import Flow


class InstallDevPubkeyFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.choose_file)

    async def choose_file(self):
        from flows.file_picker_flow import FilePickerFlow
        from files import CardSlot

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
        from common import system
        from pages.error_page import ErrorPage
        from pages.success_page import SuccessPage
        from pages.insert_microsd_page import InsertMicroSDPage
        from files import CardMissingError
        from files import CardSlot
        from utils import clear_cached_pubkey

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

                    # print('pubkey = {}'.format(hexlify(pubkey)))

                    clear_cached_pubkey()

                    result = system.set_user_firmware_pubkey(pubkey)
                    if result:
                        await SuccessPage(text='Successfully Installed!').show()
                        self.set_result(True)
                    else:
                        await ErrorPage(text='Unable to Install.').show()
                        self.set_result(False)
        except CardMissingError:
            result = await InsertMicroSDPage().show()
            if not result:
                self.back()
