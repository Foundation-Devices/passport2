# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# view_seed_words_flow.py - Confirm the user wants to see this sensitive info, then show it.

import microns
from pages import InfoPage, ErrorPage, LongTextPage, QuestionPage
from flows import Flow
from tasks import get_seed_words_task
from utils import spinner_task


class ViewSeedWordsFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.show_intro, name='ViewSeedWordsFlow')

    async def show_intro(self):
        result = await InfoPage(
            'Passport is about to display your seed words and, if defined, your passphrase.',
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
            msg = '\n'.join('         %2d. %s' % (i + 1, w) for i, w in enumerate(words))

            if passphrase is not None:
                msg += '\n\nPassphrase:\n  {}'.format(passphrase)

            result = await LongTextPage(
                card_header={'title': 'Seed Words'},
                text=msg,
                left_micron=microns.Back,
                right_micron=microns.Checkmark).show()

            # TODO: Can we Blank msg, words and passphrase?
            self.set_result(result)

            # TODO: Verify seed?  In FE, we have Verify Seed as the right button action
            # ch = await ux_show_story(msg, sensitive=True, right_btn='VERIFY')
            # if ch == 'y':
            #     seed_check = SeedCheckUX(seed_words=words, title='Verify Seed')
            #     await seed_check.show()
            #     return
        else:
            await ErrorPage(text='Unable to retrieve seed: {}'.format(error)).show()
            self.set_result(False)
