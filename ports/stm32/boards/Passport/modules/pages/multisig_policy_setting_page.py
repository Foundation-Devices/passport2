# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# multisig_policy_setting_page.py - Set the multisig policy

from pages.setting_page import SettingPage
from public_constants import TRUST_OFFER, TRUST_VERIFY, TRUST_PSBT

# Chooser for trust policy
ch = ['Ask to Import', 'Require Existing', 'Skip Verification']
values = [TRUST_OFFER, TRUST_VERIFY, TRUST_PSBT]


class MultisigPolicySettingPage(SettingPage):
    OPTIONS = [
        {'label': 'Ask to Import', 'value': TRUST_OFFER},
        {'label': 'Require Existing', 'value': TRUST_VERIFY},
        {'label': 'Skip Verification', 'value': TRUST_PSBT},
    ]

    def __init__(self, card_header=None, statusbar=None):
        super().__init__(
            card_header=card_header,
            statusbar=statusbar,
            setting_name='multisig_policy',
            options=self.OPTIONS,
            default_value=self.OPTIONS[1].get('value'))
