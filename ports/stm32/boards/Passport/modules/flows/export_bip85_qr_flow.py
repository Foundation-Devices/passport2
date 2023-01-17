# SPDX-FileCopyrightText: 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# export_bip85_qr_flow.py - Export a BIP85 seed QR code

from flows import Flow


class ExportBIP85QRFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.enter_index, name="ExportBIP85QRFlow")

    async def enter_index(self):
        from pages import TextInputPage, ShowQRPage
        from tasks import bip85_seed_task
        from utils import spinner_task
        import microns
        self.index = await TextInputPage(card_header={'title': 'Seed Number'}, numeric_only=True,
                                         initial_text='',
                                         max_length=10,
                                         left_micron=microns.Back,
                                         right_micron=microns.Checkmark).show()
        (seed, error) = await spinner_task(text='Generating Seed', task=bip85_seed_task, args=[self.index])
        if error is None:
            self.seed = seed
            self.goto(self.show_seed_words)
        else:
            self.error = error
            self.goto(self.show_error)

    async def show_seed_words(self):
        from flows import ViewSeedWordsFlow
        await ViewSeedWordsFlow(bip85_seed=self.seed, bip85_index=self.index).run()
        self.goto(self.show_qr_code)

    async def show_qr_code(self):
        from pages import ShowQRPage
        from utils import B2A
        import microns
        hex_seed = B2A(self.seed)
        print(hex_seed)
        await ShowQRPage(qr_data=B2A(self.seed), right_micron=microns.Checkmark).show()
        self.set_result(True)

    async def show_error(self):
        from pages import ErrorPage
        await ErrorPage(self.error).show()
        self.set_result(False)
