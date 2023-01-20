# SPDX-FileCopyrightText: 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# export_bip85_qr_flow.py - Export a BIP85 seed QR code

from flows import Flow


class ExportBIP85QRFlow(Flow):
    def __init__(self):
        self.index = None
        self.num_words = None
        super().__init__(initial_state=self.enter_index, name="ExportBIP85QRFlow")

    async def enter_index(self):
        from pages import TextInputPage
        import microns
        self.index = await TextInputPage(card_header={'title': 'Seed Number'}, numeric_only=True,
                                         initial_text='',
                                         max_length=10,
                                         left_micron=microns.Back,
                                         right_micron=microns.Checkmark).show()
        if self.index is None:
            self.set_result(False)
            return
        if len(self.index) == 0:
            return  # Try again
        self.goto(self.choose_num_words)

    async def choose_num_words(self):
        from pages import ChooserPage
        options = [{'label': '24 words', 'value': 24},
                   {'label': '18 words', 'value': 18},
                   {'label': '12 words', 'value': 12}]
        self.num_words = await ChooserPage(text='Number of Words', options=options).show()
        if self.num_words is None:
            self.set_result(False)
            return
        self.goto(self.generate_seed)

    async def generate_seed(self):
        from utils import spinner_task
        from tasks import bip85_seed_task
        (self.seed, self.error) = await spinner_task(text='Generating Seed', task=bip85_seed_task, args=[self.num_words, self.index])
        if self.error is None:
            self.goto(self.show_seed_words)
        else:
            self.goto(self.show_error)

    async def show_seed_words(self):
        from flows import ViewSeedWordsFlow
        await ViewSeedWordsFlow(bip85_seed=self.seed, bip85_index=self.index).run()
        self.goto(self.show_qr_code)

    async def show_qr_code(self):
        from pages import ShowQRPage
        from utils import B2A
        import microns
        await ShowQRPage(qr_data=B2A(self.seed), right_micron=microns.Checkmark).show()
        self.set_result(True)

    async def show_error(self):
        from pages import ErrorPage
        await ErrorPage(self.error).show()
        self.set_result(False)
