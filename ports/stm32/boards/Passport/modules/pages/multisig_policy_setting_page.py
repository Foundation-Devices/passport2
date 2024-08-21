# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# multisig_policy_setting_page.py - Set the multisig policy

from pages import SettingPage
from public_constants import MUSIG_ASK, MUSIG_REQUIRE, MUSIG_SKIP, MUSIG_DEFAULT
from utils import get_multisig_policy

# Chooser for trust policy
ch = ['Ask to Import', 'Require Existing', 'Skip Verification']
values = [MUSIG_ASK, MUSIG_REQUIRE, MUSIG_SKIP]


class MultisigPolicySettingPage(SettingPage):
    OPTIONS = [
        {'label': 'Ask to Import', 'value': MUSIG_ASK},
        {'label': 'Require Existing', 'value': MUSIG_REQUIRE},
        {'label': 'Skip Verification', 'value': MUSIG_SKIP},
    ]

    def __init__(self, card_header=None, statusbar=None):
        super().__init__(
            card_header=card_header,
            statusbar=statusbar,
            setting_name='multisig_policy',
            options=self.OPTIONS,
            default_value=get_multisig_policy())
