# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# random_final_word_flow.py - Flow class to track position in a menu

from flows import Flow


class RandomFinalWordFlow(Flow):
    def __init__(self, selected_words):
        self.selected_words = selected_words
        super().__init__(initial_state=self.explainer, name='RandomFinalWordFlow')

    async def explainer(self):
        from pages import InfoPage
        import microns

        result = await InfoPage('Passport will generate a random final word to complete your seed',
                                left_micron=microns.Back,
                                right_micron=microns.Forward).show()

        if not result:
            self.set_result(None)
            return

        self.goto(self.generate_word)

    async def generate_word(self):
        from predictive_utils import get_last_word
        from pages import InfoPage
        import microns
        from utils import recolor
        from styles.colors import HIGHLIGHT_TEXT_HEX
        from common import settings

        last_word = get_last_word(self.selected_words)
        styled_last_word = recolor(HIGHLIGHT_TEXT_HEX, last_word)
        save_wording = ' and save' if not settings.temporary_mode else ''
        text = 'Your final word is\n{}.\n\nImport{} this seed?'.format(styled_last_word, save_wording)
        result = await InfoPage(text=text,
                                left_micron=microns.Retry).show()

        if not result:
            self.back()
            return

        self.set_result(last_word)
