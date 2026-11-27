# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# system_test_flow.py - Runs a suite of system test flows

from flows import Flow, TestMicroSDFlow, TestCameraFlow
from pages import SuccessPage, LongTextPage, TestKeypadPage, QuestionPage, ShutdownPage
import microns


class SystemTestFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.intro, name='SystemTestFlow')

    async def intro(self):
        result = await LongTextPage(left_micron=microns.Shutdown, card_header={
            'title': 'System Test', 'icon': None, 'right_text': None},
            centered=True,
            text='\n\nThe following pages contain system tests to check if this Passport\'s hardware '
            'is working correctly.').show()
        if not result:
            await ShutdownPage().show()
        else:
            self.goto(self.test_microsd_flow)

    async def test_microsd_flow(self):
        result = await TestMicroSDFlow().run()
        if not result:
            result = await QuestionPage(text='Skip microSD test?').show()
            if result:
                self.goto(self.test_camera_flow)
            else:
                self.back()
        else:
            self.goto(self.test_camera_flow)

    async def test_camera_flow(self):
        result = await TestCameraFlow().run()
        if not result:
            self.back()
        else:
            self.goto(self.test_keypad_flow)

    async def test_keypad_flow(self):
        result = await TestKeypadPage().show()
        if not result:
            self.back()
        else:
            self.goto(self.complete)

    async def complete(self):
        result = await SuccessPage(
            'System Tests complete!',
            left_micron=microns.Shutdown,
            right_micron=None).show()
        if not result:
            await ShutdownPage().show()
