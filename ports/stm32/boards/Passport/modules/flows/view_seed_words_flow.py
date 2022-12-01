# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# view_seed_words_flow.py - Confirm the user wants to see this sensitive info, then show it.

import lvgl as lv
import microns
from pages import InfoPage, ErrorPage, LongTextPage, QuestionPage
from flows import Flow
from tasks import get_seed_words_task
from utils import spinner_task
import stash


class ViewSeedWordsFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.show_intro, name='ViewSeedWordsFlow')

    async def show_intro(self):
        result = await InfoPage(
            icon=lv.LARGE_ICON_SEED,
            text='Passport is about to display your seed words and, if defined, your passphrase.',
            left_micron=microns.Back, right_micron=microns.Forward).show()

        if result:
            self.goto(self.confirm_show)
        else:
            self.set_result(False)

    async def confirm_show(self):
        result = await QuestionPage(
            'Anyone who knows these words can control your funds.\n\nDisplay this sensitive information?').show()
        if result:
            self.goto(self.show_seed_words)
        else:
            self.set_result(False)

    async def show_seed_words(self):

        (words, passphrase, error) = await spinner_task('Retrieving Seed', get_seed_words_task)
        if error is None and words is not None:
            from pages import SeedWordsListPage
            result = await SeedWordsListPage(words=words).show()
            if stash.bip39_passphrase != '':
                await InfoPage(text='Passphrase: {}'.format(stash.bip39_passphrase)).show()
            self.set_result(result)
        else:
            await ErrorPage(text='Unable to retrieve seed: {}'.format(error)).show()
            self.set_result(False)
