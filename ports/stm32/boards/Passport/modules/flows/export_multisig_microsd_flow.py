# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# export_multisig_microsd_flow.py - Export a multisig wallet via microSD

from flows import Flow


class ExportMultisigMicrosdFlow(Flow):
    def __init__(self, context=None):
        from multisig_wallet import MultisigWallet
        super().__init__(initial_state=self.create_file, name='ExportMultisigMicrosdFlow')

        self.storage_idx = context
        self.ms = MultisigWallet.get_by_idx(self.storage_idx)
        self.ms_text = self.ms.to_file()
        self.fname = None

    async def create_file(self):
        from files import CardSlot, CardMissingError
        from pages import ErrorPage
        from utils import file_exists

        multisig_num = 1

        while True:
            try:
                with CardSlot() as card:
                    path = card.get_sd_root()
                    # Make a unique filename
                    while True:
                        self.file_path = '{}/{}-multisig-{}.txt'.format(path,
                                                                        self.ms.name,
                                                                        multisig_num)
                        self.file_path = self.file_path.replace(' ', '_')
                        # Ensure filename doesn't already exist
                        if not file_exists(self.file_path):
                            break

                        # Ooops...that exists, so increment and try again
                        multisig_num += 1

                    # Do actual write
                    with open(self.file_path, 'w') as fd:
                        fd.write(self.ms_text)
                self.goto(self.show_success)
                return

            except CardMissingError:
                self.goto(self.show_insert_microsd_error)
                return
            except Exception as e:
                self.error = e.args[0]
                await ErrorPage(text=self.error).show()
                self.set_result(False)
                return

    async def show_insert_microsd_error(self):
        result = await InsertMicroSDPage().show()
        if not result:
            self.set_result(False)
        else:
            self.goto(self.create_file)

    async def show_success(self):
        from pages import SuccessPage
        await SuccessPage(text='Saved multisig config as {}.'.format(self.file_path)).show()
        self.set_result(True)
