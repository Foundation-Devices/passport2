# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Host tests: copying a PSBT file from microSD always reports a result."""

import asyncio
import runpy
import sys
import types
from pathlib import Path

import pytest


MODULES = Path(__file__).resolve().parents[2]
PSBT = b'psbt\xff' + bytes(range(40))


class CardMissingError(RuntimeError):
    pass


class Error:
    PSBT_TOO_LARGE = 'too large'
    PSBT_INVALID = 'invalid'
    MICROSD_CARD_MISSING = 'card missing'


class BadDecoder:
    def more(self, data):
        raise ValueError('bad encoding')


@pytest.fixture
def task(monkeypatch):
    written = bytearray()
    card = {'missing': False}

    class CardSlot:
        def __enter__(self):
            if card['missing']:
                raise CardMissingError()
            return self

        def __exit__(self, *args):
            return False

    class SFFile:
        def __init__(self, offset, max_size):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        async def erase(self):
            pass

        def write(self, data):
            written.extend(data)

    stubs = {
        'public_constants': types.SimpleNamespace(MAX_TXN_LEN=1024),
        'errors': types.SimpleNamespace(Error=Error),
        'files': types.SimpleNamespace(CardSlot=CardSlot, CardMissingError=CardMissingError),
        'sffile': types.SimpleNamespace(SFFile=SFFile),
        'utils': types.SimpleNamespace(HexStreamer=BadDecoder, Base64Streamer=BadDecoder,
                                       HexWriter='hex', Base64Writer='base64'),
    }
    for name, stub in stubs.items():
        monkeypatch.setitem(sys.modules, name, stub)

    copy = runpy.run_path(str(MODULES / 'tasks/copy_psbt_file_to_external_flash_task.py'))[
        'copy_psbt_file_to_external_flash_task']

    def run(path):
        results = []

        async def on_done(*result):
            results.append(result)

        asyncio.run(copy(on_done, None, str(path), 0))
        return results

    return types.SimpleNamespace(run=run, written=written, card=card)


@pytest.mark.parametrize('contents', [
    b'',                                   # empty file
    b'\xef\xbb\xbf' + PSBT,                # leading BOM
    b'  ' + PSBT,                          # leading whitespace
    b'not a psbt at all',
    b'70736274ff' + b'zz' * 20,            # hex prefix, then bad hex
    b'cHNidP' + b'!' * 20,                 # base64 prefix, then bad base64
])
def test_unreadable_file_is_reported_invalid(task, tmp_path, contents):
    path = tmp_path / 'tx.psbt'
    path.write_bytes(contents)
    assert task.run(path) == [(0, None, Error.PSBT_INVALID)]


def test_missing_card_is_reported(task, tmp_path):
    path = tmp_path / 'tx.psbt'
    path.write_bytes(PSBT)
    task.card['missing'] = True
    assert task.run(path) == [(0, None, Error.MICROSD_CARD_MISSING)]


def test_oversized_file_is_reported(task, tmp_path):
    path = tmp_path / 'tx.psbt'
    path.write_bytes(PSBT + bytes(2048))
    assert task.run(path) == [(0, None, Error.PSBT_TOO_LARGE)]


def test_binary_psbt_is_copied(task, tmp_path):
    path = tmp_path / 'tx.psbt'
    path.write_bytes(PSBT)
    [(length, encoder, error)] = task.run(path)
    assert (length, error) == (len(PSBT), None)
    assert encoder(b'x') == b'x'
    assert bytes(task.written) == PSBT
