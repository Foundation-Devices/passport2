# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# export_derived_key_flow.py - Export a derived key

from flows import Flow


class ExportDerivedKeyFlow(Flow):
    def __init__(self, context=None):
        self.key = context
        self.num_words = None
        self.seed = None
        super().__init__(initial_state=self.choose_num_words, name="NewDerivedKeyFlow")

    async def choose_num_words(self):
        from pages import ChooserPage
        options = [{'label': '24 words', 'value': 24},
                   {'label': '12 words', 'value': 12}]
        self.num_words = await ChooserPage(card_header={'title': 'Number of Words'}, options=options).show()
        if self.num_words is None:
            self.set_result(False)
            return
        self.goto(self.generate_key)

    async def generate_key(self):
        from utils import spinner_task
        from tasks import bip85_seed_task
        from pages import ErrorPage
        (self.seed, error) = await spinner_task(text='Generating Seed',
                                                     task=bip85_seed_task,
                                                     args=[self.num_words, self.key['index']])
        if self.error is None:
            self.goto(self.show_seed_words)
        else:
            await ErrorPage(error).show()
            self.set_result(False)

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
