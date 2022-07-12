# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# options_chooser_page.py - Chooser to select between several options (limited practically to 2-3 by screen space)


import lvgl as lv
from pages import ChooserPage
import microns


class OptionsChooserPage(ChooserPage):
    def __init__(
            self,
            text='Select Something',
            options=[],
            icon=lv.LARGE_ICON_INFO,
            default_idx=0,
            left_micron=None,
            right_micron=microns.Checkmark):

        super().__init__(
            options=options,
            icon=icon,
            text=text,
            center=True,
            item_icon=None,
            initial_value=options[default_idx].get('value'),
            left_micron=left_micron,
            right_micron=right_micron)
