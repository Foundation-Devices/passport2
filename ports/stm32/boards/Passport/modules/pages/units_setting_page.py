# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# units_setting_page.py - Set the current units (e.g., Sats/Bitcoin) based on the active chain

from pages import SettingPage
from constants import UNIT_TYPE_BTC, UNIT_TYPE_SATS
import chains


class UnitsSettingPage(SettingPage):

    def __init__(self, card_header=None, statusbar=None):
        chain = chains.current_chain()
        options = [
            {'label': chain.ctype, 'value': UNIT_TYPE_BTC},
            {'label': chain.ctype_sats, 'value': UNIT_TYPE_SATS}
        ]

        super().__init__(
            card_header=card_header,
            statusbar=statusbar,
            setting_name='units',
            options=options,
            default_value=options[0].get('value'))
