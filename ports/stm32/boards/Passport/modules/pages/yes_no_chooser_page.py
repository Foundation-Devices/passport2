# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# yes_no_chooser_page.py - Chooser to select a yes or not response.


import lvgl as lv
from pages import ChooserPage
import microns


class YesNoChooserPage(ChooserPage):
    def __init__(self,
                 yes_text='Yes',
                 no_text='No',
                 icon=None,
                 text=None,
                 initial_value=True,
                 left_micron=None,
                 right_micron=None):
        options = [
            {'label': yes_text, 'value': True},
            {'label': no_text, 'value': False}
        ]
        if not initial_value:
            options.reverse()

        super().__init__(
            options=options,
            icon=icon,
            text=text,
            center=True,
            item_icon=None,
            initial_value=options[0].get('value'),
            left_micron=left_micron,
            right_micron=right_micron)
