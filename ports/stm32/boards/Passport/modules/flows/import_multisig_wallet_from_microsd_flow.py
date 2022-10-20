# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# import_multisig_wallet_from_microsd_flow.py - Import a multisig wallet from microSD

from flows import Flow


class ImportMultisigWalletFromMicroSDFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.choose_wallet_file, name='ImportMultisigWalletFromMicroSDFlow')
        self.ms = None
        self.error = None

    async def choose_wallet_file(self):
        from flows import FilePickerFlow
        from files import CardSlot
        from pages import InsertMicroSDPage, ErrorPage
        from tasks import read_file_task
        from utils import spinner_task
        from errors import Error
        from multisig_wallet import MultisigWallet

        root_path = CardSlot.get_sd_root()

        result = await FilePickerFlow(initial_path=root_path, show_folders=True).run()
        if result is None:
            self.set_result(False)
            return

        _filename, full_path, is_folder = result
        if not is_folder:
            result = await spinner_task(
                'Reading File',
                read_file_task,
                args=[full_path])
            (data, error) = result
            if error is None:
                try:
                    self.ms = MultisigWallet.from_file(data)
                except BaseException as e:
                    self.error = e.args[0]
                    if self.error is None:
                        self.error = "Unknown Error"
                    self.goto(self.show_error)
                    return
                # print('New MS: {}'.format(self.ms.serialize()))

                self.goto(self.do_import)
            elif error is Error.MICROSD_CARD_MISSING:
                result = await InsertMicroSDPage().show()
                if not result:
                    self.set_result(False)
                    return
            elif error is Error.FILE_WRITE_ERROR:
                await ErrorPage(text='Unable to read multisig config file from microSD card.').show()
                self.set_result(False)

    async def do_import(self):
        from flows import ImportMultisigWalletFlow

        # Show the wallet to the user for import
        result = await ImportMultisigWalletFlow(self.ms).run()
        self.set_result(result)

    async def show_error(self):
        from pages import ErrorPage
        await ErrorPage(text=self.error).show()
        self.error = None
        self.reset(self.choose_wallet_file)
