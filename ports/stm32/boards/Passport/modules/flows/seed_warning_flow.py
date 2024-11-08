# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# seed_warning_flow.py - Confirm the user wants to see this sensitive info.

from flows import Flow


class SeedWarningFlow(Flow):
    def __init__(self, mention_passphrase=False,
                 action_text="display your seed words",
                 continue_text=None,
                 info_type_text=None,
                 initial=False,
                 allow_skip=True,
                 key_manager=False):
        self.mention_passphrase = mention_passphrase
        self.action_text = action_text or "display your seed words"
        self.continue_text = continue_text or "funds"
        self.info_type_text = info_type_text or "these words"
        self.allow_skip = allow_skip
        self.initial = initial
        self.key_manager = key_manager
        initial_state = self.show_skippable if (initial and allow_skip) else self.show_intro
        super().__init__(initial_state=initial_state, name='SeedWarningFlow')

    async def show_skippable(self):
        from pages import InfoPage
        import microns
        import lvgl as lv

        text = '''After setup, your seed words can be viewed in the advanced menu.

Would you like to view them now?'''

        left_micron = microns.Cancel if self.allow_skip else None

        result = await InfoPage(text=text,
                                icon=lv.LARGE_ICON_SEED,
                                left_micron=microns.Cancel).show()

        if not result:
            self.set_result(False)
            return

        self.set_result(True)

    async def show_intro(self):
        import lvgl as lv
        import microns
        from pages import InfoPage
        from utils import is_passphrase_active

        if self.mention_passphrase and is_passphrase_active():
            text = 'Passport is about to {} and passphrase'.format(self.action_text)
        else:
            text = 'Passport is about to {}'.format(self.action_text)

        # Empty microns have no action, so backing out isn't allowed
        left_micron = microns.Back if self.allow_skip else None

        right_micron = microns.Checkmark if self.key_manager else microns.Forward

        result = await InfoPage(
            icon=lv.LARGE_ICON_SEED, text=text,
            left_micron=left_micron, right_micron=right_micron).show()

        if not result:
            self.set_result(False)
            return

        if self.initial:
            self.goto(self.prompt_backup)
            return

        if self.key_manager:
            self.set_result(True)
            return

        self.goto(self.confirm_show)

    async def prompt_backup(self):
        from pages import InfoPage
        import microns

        text = 'Write down these words on the backup card provided. ' \
               'Store the card securely and never take a photo of it.'

        result = await InfoPage(text, left_micron=microns.Back).show()

        if not result:
            self.back()
            return

        self.goto(self.confirm_show)

    async def confirm_show(self):
        from pages import QuestionPage
        import microns

        text = 'Anyone requesting you expose {} outside Passport ' \
               'will gain full control over your {}. Take care.' \
               .format(self.info_type_text, self.continue_text)
        left_micron = microns.Cancel

        if not self.allow_skip:
            left_micron = None
        else:
            text += '\n\nContinue?'

        result = await QuestionPage(text, left_micron=left_micron).show()
        self.set_result(result)
