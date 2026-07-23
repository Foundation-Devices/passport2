# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Test backup restore settings filtering.

from tasks.restore_backup_task import restore_settings_from_backup


class FakeSettings:
    def __init__(self):
        self.values = {}

    def set(self, key, value):
        self.values[key] = value


vals = {
    'chain': 'BTC',
    'xfp': 'top-level metadata is ignored here',
    'setting.xfp': 0x11111111,
    'setting.xpub': 'attacker-xpub',
    'setting.root_xfp': 0x22222222,
    'setting.units': 'sats',
    'setting.backup_quiz': True,
}

settings = FakeSettings()
restore_settings_from_backup(vals, settings)

assert settings.values == {
    'units': 'sats',
    'backup_quiz': True,
}

return_value.write(b'OK')
