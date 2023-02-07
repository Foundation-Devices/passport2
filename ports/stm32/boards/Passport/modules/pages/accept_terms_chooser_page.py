# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# accept_terms_chooser_page.py - Chooser to accept terms or not.


import lvgl as lv
from pages import ChooserPage


class AcceptTermsChooserPage(ChooserPage):
    OPTIONS = [
        {'label': 'Accept', 'value': 'accept'},
        {'label': 'Do Not Accept', 'value': 'do_not_accept'}
    ]

    def __init__(self):
        super().__init__(
            options=self.OPTIONS,
            icon=lv.LARGE_ICON_INFO,
            text='I have read and accept the Terms of Use.',
            center=True,
            item_icon=None,
            initial_value=self.OPTIONS[0].get('value'))
