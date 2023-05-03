# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# view_seed_words_flow.py - Confirm the user wants to see this sensitive info, then show it.

from flows import Flow


class ViewSeedWordsFlow(Flow):
    def __init__(self, external_key=None):
        self.external_key = external_key
        super().__init__(initial_state=self.show_warning, name='ViewSeedWordsFlow')

    async def show_warning(self):
        from flows import SeedWarningFlow

        mention_passphrase = False if self.external_key else True
        result = await SeedWarningFlow(mention_passphrase=mention_passphrase).run()

        if not result:
            self.set_result(False)

        self.goto(self.show_seed_words)

    async def show_seed_words(self):
        from flows import GetSeedWordsFlow
        from pages import SeedWordsListPage, InfoPage
        import stash

        words = await GetSeedWordsFlow(self.external_key).run()

        if words is None:
            self.set_result(False)
            return

        result = await SeedWordsListPage(words=words).show()
        if stash.bip39_passphrase != '' and not self.external_key:
            await InfoPage(text='Passphrase: {}'.format(stash.bip39_passphrase)).show()
        self.set_result(result)
