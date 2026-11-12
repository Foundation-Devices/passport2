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
from uio import BytesIO, StringIO
from utils import get_backup_code_as_password

CODE = [1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5]
PASSWORD = get_backup_code_as_password(CODE)


def render_text():
    # Built at run time like render_backup_contents(), so the string is new
    # and not shared with a literal: encode() shares its buffer, and the flow
    # wipes that buffer.
    out = StringIO()
    out.write('# Passport backup file! DO NOT CHANGE.\n')
    out.write('raw_secret = "%s"\n' % ('ab' * 16))
    return out.getvalue()


# An independent copy, since the flow wipes the text it is given.
EXPECTED = bytes(bytearray(render_text().encode()))


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


class FailingCipher:
    # Keeps what it was asked to encrypt, then fails as an allocation would.
    def __init__(self):
        self.given = []

    def encrypt(self, data):
        self.given.append(data)
        raise MemoryError


def decrypt(data):
    return compat7z.Builder().read_file(BytesIO(data), PASSWORD, 10000)


def run_write_fn(render, builder, output):
    original = (export.render_backup_contents, compat7z.Builder)
    try:
        export.render_backup_contents = render
        compat7z.Builder = builder
        backup_module.open = lambda filename, mode: output
        BackupCommonFlow.write_fn(Holder(), 'backup.7z')
    finally:
        export.render_backup_contents, compat7z.Builder = original
        del backup_module.open


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

    def render():
        captured['text'] = render_text()
        return captured['text']

    run_write_fn(render, CapturingBuilder, output)

    # Check the bytes themselves: MicroPython caches a bytes object's hash,
    # which wiping in place leaves stale, so == against zeros would mislead.
    assert len(captured['plaintext']) == len(EXPECTED) and not any(captured['plaintext'])
    assert len(captured['key']) == 32 and not any(captured['key'])
    # The rendered text shares the plaintext's buffer, so it is cleared too.
    assert all(ord(c) == 0 for c in captured['text'])
    assert decrypt(output.written.getvalue()) == ('passport-backup.txt', EXPECTED)


def check_scratch_block_wiped_on_failure():
    # A partial last block is copied into a scratch block. If encrypting it
    # fails, the scratch block must still be cleared.
    zz = compat7z.Builder(password=PASSWORD)
    cipher = FailingCipher()
    zz.aes = cipher
    try:
        zz.add_data(bytes(range(1, 7)))
    except MemoryError:
        pass
    else:
        assert False, 'encrypting did not fail'
    assert len(cipher.given) == 1 and len(cipher.given[0]) == 16
    assert not any(cipher.given[0])


def check_write_fn_wipes_on_failure():
    # When encrypting fails, the plaintext and the key are still wiped, and
    # the error reaches the caller.
    captured = {}

    class FailingBuilder(compat7z.Builder):
        def add_data(self, raw):
            captured['plaintext'] = raw
            self.aes = FailingCipher()
            super().add_data(raw)

        def wipe_key(self):
            captured['key'] = self.key
            super().wipe_key()

    output = Output()
    try:
        run_write_fn(render_text, FailingBuilder, output)
    except MemoryError:
        pass
    else:
        assert False, 'write_fn did not fail'
    assert len(captured['plaintext']) == len(EXPECTED) and not any(captured['plaintext'])
    assert len(captured['key']) == 32 and not any(captured['key'])
    assert not output.written.getvalue()


original_noise = common.noise
try:
    common.noise = MockNoise
    check_round_trips()
    check_write_fn_wipes()
    check_scratch_block_wiped_on_failure()
    check_write_fn_wipes_on_failure()
finally:
    common.noise = original_noise

return_value.write(b'OK')
