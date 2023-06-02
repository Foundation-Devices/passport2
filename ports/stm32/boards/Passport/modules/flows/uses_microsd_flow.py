# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# uses_microsd_flow.py - Base class for all UI flows

from flows import Flow


class UsesMicroSDFlow(Flow):
    def __init__(self,
                 initial_state=None,
                 name='UsesMicroSDFlow',
                 settings_key=None,
                 statusbar=None,
                 automatic=False,
                 return_bool=True,
                 back_out=False):

        self.automatic = automatic
        self.return_bool = return_bool
        self.back_out = back_out

        super().__init__(initial_state=initial_state,
                         name=name,
                         settings_key=settings_key,
                         statusbar=statusbar)

    async def show_card_missing(self):
        from pages import InsertMicroSDPage

        # This makes the return type consistent with the subclass
        if self.return_bool:
            result = False
        else:
            result = None

        if self.automatic:
            self.set_result(result)
            return

        retry = await InsertMicroSDPage().show()
        if retry or self.back_out:
            self.back()
        else:
            self.set_result(result)
