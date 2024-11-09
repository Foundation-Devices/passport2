# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# recovery_mode_chooser_page.py - Chooser to select the type of password for recovering a backup.


from pages import ChooserPage
from Enum import enum
import microns

RecoveryMode = enum(
    'BACKUP_CODE_20_DIGITS',
    'BACKUP_PASSWORD_6_WORDS'
)


class RecoveryModeChooserPage(ChooserPage):
    OPTIONS = [
        {'label': 'Backup Code\n(20 digits)', 'value': RecoveryMode.BACKUP_CODE_20_DIGITS},
        {'label': 'Backup Password\n(6 words)', 'value': RecoveryMode.BACKUP_PASSWORD_6_WORDS},
    ]

    def __init__(self, card_header={'title': 'Recovery Mode'}, initial_value=None,
                 left_micron=microns.Back, right_micron=microns.Forward):
        super().__init__(
            card_header=card_header,
            options=self.OPTIONS,
            initial_value=initial_value or self.OPTIONS[0].get('value'),
            left_micron=left_micron, right_micron=right_micron)
