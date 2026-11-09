# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Backup creation still produces a readable backup, and leaves neither the
# plaintext nor the backup key behind once it is encrypted.

import common
import compat7z
import export
import flows.backup_common_flow as backup_module
from flows.backup_common_flow import BackupCommonFlow
from uio import BytesIO
from utils import get_backup_code_as_password

CODE = [1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5]
PASSWORD = get_backup_code_as_password(CODE)
TEXT = '# Passport backup file! DO NOT CHANGE.\nraw_secret = "00"\n'


class MockNoise:
    # The simulator has no noise source; any salt and IV will do here.
    ALL = 0

    @staticmethod
    def random_bytes(buf, _source):
        for i in range(len(buf)):
            buf[i] = (i * 37 + 11) & 0xff


class Output:
    def __init__(self):
        self.written = BytesIO()

    def __enter__(self):
        return self.written

    def __exit__(self, *args):
        return False


class Holder:
    backup_code = CODE


def decrypt(data):
    return compat7z.Builder().read_file(BytesIO(data), PASSWORD, 10000)


def check_round_trips():
    # Whole blocks, a partial last block and a single byte all round-trip.
    for size in (1, 15, 16, 17, 100, 333):
        payload = bytes([(i * 31 + 7) & 0xff for i in range(size)])
        zz = compat7z.Builder(password=PASSWORD)
        zz.add_data(payload)
        hdr, footer = zz.save('x.txt')
        assert decrypt(hdr + zz.body + footer) == ('x.txt', payload), size


def check_write_fn_wipes():
    # The flow wipes the plaintext and the key, but only after encrypting.
    captured = {}
    output = Output()

    class CapturingBuilder(compat7z.Builder):
        def add_data(self, raw):
            captured['plaintext'] = raw
            super().add_data(raw)

        def wipe_key(self):
            captured['key'] = self.key
            super().wipe_key()

    original = (export.render_backup_contents, compat7z.Builder)
    try:
        export.render_backup_contents = lambda: TEXT
        compat7z.Builder = CapturingBuilder
        backup_module.open = lambda filename, mode: output
        BackupCommonFlow.write_fn(Holder(), 'backup.7z')
    finally:
        export.render_backup_contents, compat7z.Builder = original
        del backup_module.open

    # Check the bytes themselves: MicroPython caches a bytes object's hash,
    # which wiping in place leaves stale, so == against zeros would mislead.
    assert len(captured['plaintext']) == len(TEXT) and not any(captured['plaintext'])
    assert len(captured['key']) == 32 and not any(captured['key'])
    assert decrypt(output.written.getvalue()) == ('passport-backup.txt', TEXT.encode())


original_noise = common.noise
try:
    common.noise = MockNoise
    check_round_trips()
    check_write_fn_wipes()
finally:
    common.noise = original_noise

return_value.write(b'OK')
