# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

import builtins
import importlib.util
import os
import sys
import types

import pytest


MODULES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
READER_PATH = os.path.join(MODULES_DIR, 'backup_reader.py')
sys.path.insert(1, MODULES_DIR)

from errors import Error


class CardMissingError(Exception):
    pass


class CardSlot:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


class FakeFile:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


def load_reader(monkeypatch, check_headers=None, read_file=None, card_slot=CardSlot):
    calls = types.SimpleNamespace(header=0, reads=[])
    compat7z = types.ModuleType('compat7z')

    def default_check_headers(_fd):
        calls.header += 1

    compat7z.check_file_headers = check_headers or default_check_headers

    class Builder:
        def read_file(self, fd, password, max_size, progress_fcn=None):
            calls.reads.append((fd, password, max_size, progress_fcn))
            if read_file is not None:
                return read_file(fd, password, max_size, progress_fcn)
            return 'passport-backup.txt', b'# Passport backup\n'

    compat7z.Builder = Builder

    files = types.ModuleType('files')
    files.CardSlot = card_slot
    files.CardMissingError = CardMissingError

    constants = types.ModuleType('constants')
    constants.MAX_BACKUP_FILE_SIZE = 4096

    monkeypatch.setitem(sys.modules, 'compat7z', compat7z)
    monkeypatch.setitem(sys.modules, 'files', files)
    monkeypatch.setitem(sys.modules, 'constants', constants)

    spec = importlib.util.spec_from_file_location('backup_reader_under_test', READER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.read_backup_file, calls


def test_reads_and_validates_backup_without_importing_device_state(monkeypatch):
    fd = FakeFile()
    device_state = types.SimpleNamespace(writes=[])
    common = types.ModuleType('common')
    common.device_state = device_state
    monkeypatch.setitem(sys.modules, 'common', common)
    monkeypatch.setattr(builtins, 'open', lambda *_args, **_kwargs: fd)
    read_backup_file, calls = load_reader(monkeypatch)

    contents, error = read_backup_file('backup-code', 'backup.7z')

    assert contents == b'# Passport backup\n'
    assert error is None
    assert calls.header == 1
    assert calls.reads == [(fd, 'backup-code', 4096, None)]
    assert fd.closed
    assert device_state.writes == []


@pytest.mark.parametrize(
    ('failure', 'expected_error'),
    (
        (OSError('read failed'), Error.FILE_READ_ERROR),
        (ValueError('bad header'), Error.INVALID_BACKUP_FILE_HEADER),
    ))
def test_classifies_header_failures(monkeypatch, failure, expected_error):
    fd = FakeFile()
    monkeypatch.setattr(builtins, 'open', lambda *_args, **_kwargs: fd)

    def reject_header(_fd):
        raise failure

    read_backup_file, _calls = load_reader(monkeypatch, check_headers=reject_header)

    assert read_backup_file('backup-code', 'backup.7z') == (None, expected_error)
    assert fd.closed


@pytest.mark.parametrize(
    ('failure', 'expected_error'),
    (
        (OSError('read failed'), Error.FILE_READ_ERROR),
        (ValueError('wrong code or damaged body'), Error.INVALID_BACKUP_CODE),
    ))
def test_classifies_decryption_failures(monkeypatch, failure, expected_error):
    fd = FakeFile()
    monkeypatch.setattr(builtins, 'open', lambda *_args, **_kwargs: fd)

    def reject_body(_fd, _password, _max_size, _progress_fcn):
        raise failure

    read_backup_file, _calls = load_reader(monkeypatch, read_file=reject_body)

    assert read_backup_file('backup-code', 'backup.7z') == (None, expected_error)
    assert fd.closed


def test_rejects_plaintext_that_is_not_a_passport_backup(monkeypatch):
    fd = FakeFile()
    monkeypatch.setattr(builtins, 'open', lambda *_args, **_kwargs: fd)

    def invalid_plaintext(_fd, _password, _max_size, _progress_fcn):
        return 'passport-backup.txt', b'not a Passport backup'

    read_backup_file, _calls = load_reader(monkeypatch, read_file=invalid_plaintext)

    assert read_backup_file('backup-code', 'backup.7z') == (None, Error.INVALID_BACKUP_CODE)
    assert fd.closed


def test_classifies_card_removal_and_open_failures(monkeypatch):
    class MissingCardSlot:
        def __enter__(self):
            raise CardMissingError

        def __exit__(self, exc_type, exc_value, traceback):
            return False

    read_backup_file, _calls = load_reader(monkeypatch, card_slot=MissingCardSlot)
    assert read_backup_file('backup-code', 'backup.7z') == (None, Error.MICROSD_CARD_MISSING)

    def fail_open(*_args, **_kwargs):
        raise OSError('open failed')

    monkeypatch.setattr(builtins, 'open', fail_open)
    read_backup_file, _calls = load_reader(monkeypatch)
    assert read_backup_file('backup-code', 'backup.7z') == (None, Error.FILE_READ_ERROR)
