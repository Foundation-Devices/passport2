# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from settings import DATA_SIZE, Settings


class OversizedSettings:
    def __init__(self):
        self.curr_dict = {'value': 'x' * DATA_SIZE}

    def next_addr(self):
        raise RuntimeError('Oversized settings reached flash slot selection')


settings = OversizedSettings()

try:
    Settings.save(settings)
except ValueError as exc:
    assert str(DATA_SIZE) in str(exc)
else:
    raise RuntimeError('Oversized settings should fail before selecting a flash slot')

return_value.write(b'OK')
