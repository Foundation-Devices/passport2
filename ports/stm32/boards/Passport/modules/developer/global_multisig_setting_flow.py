# SPDX-FileCopyrightText: © 2024 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# global_multisig_setting_flow.py - decide if multisig-related settings should be global across keys

import lvgl as lv
from pages import LongTextPage, SettingPage
from flows import Flow
from utils import check_and_set_global_multisigs
from styles.colors import DEFAULT_LARGE_ICON_COLOR


class GlobalMultisigSettingFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.explain, name='GlobalMultisigSettingFlow')

    async def explain(self):
        text = '\nThis setting determines if multisigs and multisig policy will be ' \
               'shared by the main key and all temporary keys activated on the device.'
        result = await LongTextPage(text=text,
                                    centered=True,
                                    icon=lv.LARGE_ICON_INFO,
                                    icon_color=DEFAULT_LARGE_ICON_COLOR).show()

        if not result:
            self.set_result(False)
            return

        self.goto(self.select_setting)

    async def select_setting(self):
        options = [
            {'label': 'Enable Global Multisigs', 'value': True},
            {'label': 'Disable Global Multisigs', 'value': False}
        ]

        await SettingPage(options=options,
                          setting_name='global_multisigs',
                          default_value=False,
                          on_change=check_and_set_global_multisigs).show()

        self.set_result(True)
