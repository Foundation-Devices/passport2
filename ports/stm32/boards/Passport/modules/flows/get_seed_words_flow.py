# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# get_seed_words_flow.py - Get seed words from the root or an external key

from flows import Flow


class GetSeedWordsFlow(Flow):
    def __init__(self, external_key=None):
        super().__init__(initial_state=self.get_words, name='GetSeedWordsFlow')
        self.external_key = external_key

    async def get_words(self):
        from tasks import get_seed_words_task
        from utils import spinner_task, get_words_from_seed
        from pages import ErrorPage

        if self.external_key:
            (words, error) = get_words_from_seed(self.external_key)
        else:
            (words, error) = await spinner_task(text='Retrieving Seed',
                                                task=get_seed_words_task)

        if error is not None or words is None:
            await ErrorPage(text='Unable to retrieve seed: {}'.format(error)).show()
            self.set_result(None)
            return
        self.set_result(words)
