# SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundation.xyz>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Test the external settings module.

import common
import ujson

from ext_settings import ExtSettings, SettingsOutOfSpace


class FakeFlash:
    def __init__(self, size):
        self.data = bytearray(b'\xff' * size)

    def read(self, address, buf):
        buf[:] = self.data[address:address + len(buf)]

    def write(self, address, buf):
        for i in range(len(buf)):
            self.data[address + i] &= buf[i]

    def wait_done(self):
        pass

    def is_busy(self):
        return False

    def sector_erase(self, address):
        self.data[address:address + 4096] = b'\xff' * 4096


SLOT_SIZE = 512
SLOT_START = 4096
FLASH_SIZE = SLOT_START + (SLOT_SIZE * 2)
SLOTS = range(SLOT_START, FLASH_SIZE, SLOT_SIZE)

common.sf = FakeFlash(FLASH_SIZE)

settings = ExtSettings(slots=SLOTS, slot_size=SLOT_SIZE)
names = ['\ube44\ud2b8\ucf54\uc778 \uae08\uace0', 'Multisig \u2018Vault\u2019']
settings.set('multisig', [{'name': name} for name in names])
settings.save()

loaded = ExtSettings(slots=SLOTS, slot_size=SLOT_SIZE)
loaded.load()
assert [entry['name'] for entry in loaded.get('multisig')] == names

# A payload that exactly fills the encoded data area must still round-trip.
common.sf = FakeFlash(FLASH_SIZE)
exact = ExtSettings(slots=SLOTS, slot_size=SLOT_SIZE)
exact.current['value'] = ''
json_overhead = len(ujson.dumps(exact.current).encode('utf8'))
exact_value = 'x' * (exact.max_json_len - json_overhead)
exact.current['value'] = exact_value
exact.save()

loaded = ExtSettings(slots=SLOTS, slot_size=SLOT_SIZE)
loaded.load()
assert loaded.get('value') == exact_value

# An oversized payload must fail before selecting or writing a slot.
common.sf = FakeFlash(FLASH_SIZE)
oversized = ExtSettings(slots=SLOTS, slot_size=SLOT_SIZE)
oversized.current['value'] = exact_value + 'x'

try:
    oversized.save()
except SettingsOutOfSpace:
    pass
else:
    raise RuntimeError('Oversized settings should fail before writing')

assert common.sf.data == bytearray(b'\xff' * FLASH_SIZE)

return_value.write(b'OK')
