# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# view_seed_words_flow.py - Confirm the user wants to see this sensitive info, then show it.

from flows import Flow


class ViewSeedWordsFlow(Flow):
    def __init__(self, external_key=None):
        self.external_key = external_key
        super().__init__(initial_state=self.show_intro, name='ViewSeedWordsFlow')

    async def show_intro(self):
        import lvgl as lv
        import microns
        from pages import InfoPage

        if self.external_key:
            text = 'Passport is about to display your seed words.'
        else:
            text = 'Passport is about to display your seed words and, if defined, your passphrase.'
        result = await InfoPage(
            icon=lv.LARGE_ICON_SEED, text=text,
            left_micron=microns.Back, right_micron=microns.Forward).show()

        if result:
            self.goto(self.confirm_show)
        else:
            self.set_result(False)

    async def confirm_show(self):
        from pages import QuestionPage

        result = await QuestionPage(
            'Anyone who knows these words can control your funds.\n\nDisplay this sensitive information?').show()
        if result:
            self.goto(self.show_seed_words)
        else:
            self.set_result(False)

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
