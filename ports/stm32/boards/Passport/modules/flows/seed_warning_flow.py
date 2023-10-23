# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# seed_warning_flow.py - Confirm the user wants to see this sensitive info.

from flows import Flow


class SeedWarningFlow(Flow):
    def __init__(self, mention_passphrase=False,
                 action_text="display your seed words",
                 continue_text=None,
                 initial=False):
        self.mention_passphrase = mention_passphrase
        self.action_text = action_text
        self.continue_text = continue_text or "control your funds"
        initial_state = self.show_initial if initial else self.show_intro
        super().__init__(initial_state=initial_state, name='SeedWarningFlow')

    async def show_initial(self):
        from pages import InfoPage
        import microns
        import lvgl as lv

        text = '''After setup completion, your seed words can be viewed in the advanced menu.

Would you like to view them now?'''

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
        import stash

        if self.mention_passphrase and stash.bip39_passphrase:
            text = 'Passport is about to {} and passphrase'.format(self.action_text)
        else:
            text = 'Passport is about to {}'.format(self.action_text)

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
            'Anyone who knows this information can {}.\n\nContinue?'.format(self.continue_text)).show()
        self.set_result(result)
