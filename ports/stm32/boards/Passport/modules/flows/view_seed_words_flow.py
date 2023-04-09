# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# view_seed_words_flow.py - Confirm the user wants to see this sensitive info, then show it.

from flows import Flow


class ViewSeedWordsFlow(Flow):
    def __init__(self, external_key=None, qr_option=False):
        self.external_key = external_key
        self.qr_option = qr_option
        self.mode = None
        self.words = None
        super().__init__(initial_state=self.show_warning, name='ViewSeedWordsFlow')

    async def show_warning(self):
        from flows import SeedWarningFlow
        from flows import GetSeedWordsFlow

        mention_passphrase = False if self.external_key else True
        result = await SeedWarningFlow(mention_passphrase=mention_passphrase).run()

        if not result:
            self.set_result(False)
            return

        self.words = await GetSeedWordsFlow(self.external_key).run()

        if self.words is None:
            self.set_result(False)
            return

        if self.qr_option:
            self.goto(self.choose_mode)
        else:
            self.goto(self.show_seed_words)

    async def choose_mode(self):
        from pages import ChooserPage
        from data_codecs.qr_type import QRType

        options = [{'label': 'Seed Words', 'value': self.show_seed_words},
                   {'label': 'Compact SeedQR', 'value': QRType.COMPACT_SEED_QR},
                   {'label': 'SeedQr', 'value': QRType.SEED_QR}]
        self.mode = await ChooserPage(card_header={'title': 'View'}, options=options).show()
        if self.mode is None:
            self.set_result(False)
            return

        if isinstance(self.mode, int):
            self.goto(self.show_qr)
        else:
            self.goto(self.show_seed_words)

    async def show_qr(self):
        from pages import ShowQRPage
        import microns

        await ShowQRPage(qr_type=self.mode, qr_data=self.words, right_micron=microns.Checkmark).show()
        self.goto(self.show_passphrase)

    async def show_seed_words(self):
        from pages import SeedWordsListPage

        await SeedWordsListPage(words=self.words).show()
        self.goto(self.show_passphrase)

    async def show_passphrase(self):
        import stash
        from pages import InfoPage

        if stash.bip39_passphrase != '' and not self.external_key:
            await InfoPage(text='Passphrase: {}'.format(stash.bip39_passphrase)).show()
        self.set_result(True)
