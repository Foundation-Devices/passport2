# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# spin_delay_flow.py - Show a spinner that will display until the given delay has expired.


from flows import Flow


class SpinDelayFlow(Flow):
    def __init__(self, delay_ms=5000):
        super().__init__(initial_state=self.spin, name='SpinDelayFlow')
        self.delay_ms = delay_ms

    async def spin(self):
        from utils import spinner_task
        from tasks import delay_task

        (error,) = await spinner_task(
            'Delaying for {}ms...'.format(self.delay_ms),
            delay_task,
            args=[self.delay_ms, True])

        self.goto(self.show_success)

    async def show_success(self):
        from pages import SuccessPage
        await SuccessPage(text='Delay Complete').show()
        self.set_result(True)
