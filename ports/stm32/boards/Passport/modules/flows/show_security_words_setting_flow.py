# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# show_security_words_setting_flow.py - Choose to decide to show security words at login or not.

import lvgl as lv
from flows import Flow
from pages import PINEntryPage, ChooserPage, ErrorPage, InfoPage
import microns
from common import settings
from utils import check_pin_prefix_hash, spinner_task, recolor
from public_constants import NUM_DIGITS_FOR_SECURITY_WORDS
from tasks import get_security_words_task
from styles.colors import HIGHLIGHT_TEXT_HEX


class ShowSecurityWordsSettingFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.select_setting, name='LoginFlow')

    async def select_setting(self):
        options = [
            {'label': 'Show at Login', 'value': True},
            {'label': 'Don\'t Show', 'value': False}
        ]
        initial_value = settings.get('security_words', False)

        selected_value = await ChooserPage(options=options,
                                           initial_value=initial_value).show()
        if selected_value is None:
            self.set_result(True)
            return

        if selected_value:
            self.goto(self.enter_pin)
        else:
            settings.set('security_words', False)
            self.set_result(False)

    async def enter_pin(self):
        (pin, is_done) = await PINEntryPage(
            card_header={'title': 'Enter PIN'},
            left_micron=microns.Back,
            right_micron=microns.Checkmark).show()

        if not is_done:
            self.back()
            return

        if not check_pin_prefix_hash(pin):
            await ErrorPage('Wrong PIN!').show()
            self.back()
            return

        if len(pin) < NUM_DIGITS_FOR_SECURITY_WORDS:
            await ErrorPage('Your PIN Is Too Short!').show()
            self.back()
            return

        prefix = pin[:NUM_DIGITS_FOR_SECURITY_WORDS]
        security_words, error = await spinner_task('Getting Security Words',
                                                   get_security_words_task,
                                                   args=[prefix])

        message = 'Remember these security words:\n\n'
        message += recolor(HIGHLIGHT_TEXT_HEX, ' '.join(security_words))

        await InfoPage(message).show()
        settings.set('security_words', True)

        self.back()
