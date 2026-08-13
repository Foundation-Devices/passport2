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


class ForbiddenDeviceState(types.ModuleType):
    def __getattr__(self, name):
        raise AssertionError('backup verification accessed common.{}'.format(name))


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
            return 'passport-backup.txt', bytearray(b'# Passport backup\n')

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
    return module, calls


def test_reads_and_validates_backup_without_accessing_device_state(monkeypatch):
    fd = FakeFile()
    monkeypatch.setitem(sys.modules, 'common', ForbiddenDeviceState('common'))
    monkeypatch.setattr(builtins, 'open', lambda *_args, **_kwargs: fd)
    module, calls = load_reader(monkeypatch)

    contents, error = module.read_backup_file('backup-code', 'backup.7z')

    assert contents == b'# Passport backup\n'
    assert error is None
    assert calls.header == 1
    assert calls.reads == [(fd, 'backup-code', 4096, None)]
    assert fd.closed


def test_verify_clears_plaintext_before_returning(monkeypatch):
    fd = FakeFile()
    plaintext = bytearray(b'# Passport backup\n')
    monkeypatch.setattr(builtins, 'open', lambda *_args, **_kwargs: fd)

    def return_plaintext(_fd, _password, _max_size, _progress_fcn):
        return 'passport-backup.txt', plaintext

    module, _calls = load_reader(monkeypatch, read_file=return_plaintext)

    assert module.verify_backup_file('backup-code', 'backup.7z') is None
    assert plaintext == bytearray(len(plaintext))


@pytest.mark.parametrize(
    ('failure', 'expected_error'),
    (
        (MemoryError(), Error.OUT_OF_MEMORY_ERROR),
        (OSError('read failed'), Error.FILE_READ_ERROR),
        (ValueError('bad header'), Error.INVALID_BACKUP_FILE_HEADER),
    ))
def test_classifies_header_failures(monkeypatch, failure, expected_error):
    fd = FakeFile()
    monkeypatch.setattr(builtins, 'open', lambda *_args, **_kwargs: fd)

    def reject_header(_fd):
        raise failure

    module, _calls = load_reader(monkeypatch, check_headers=reject_header)

    assert module.read_backup_file('backup-code', 'backup.7z') == (None, expected_error)
    assert fd.closed


@pytest.mark.parametrize(
    ('failure', 'expected_error'),
    (
        (MemoryError(), Error.OUT_OF_MEMORY_ERROR),
        (OSError('read failed'), Error.FILE_READ_ERROR),
        (ValueError('wrong code or damaged body'), Error.INVALID_BACKUP_CODE),
    ))
def test_classifies_decryption_failures(monkeypatch, failure, expected_error):
    fd = FakeFile()
    monkeypatch.setattr(builtins, 'open', lambda *_args, **_kwargs: fd)

    def reject_body(_fd, _password, _max_size, _progress_fcn):
        raise failure

    module, _calls = load_reader(monkeypatch, read_file=reject_body)

    assert module.read_backup_file('backup-code', 'backup.7z') == (None, expected_error)
    assert fd.closed


def test_rejects_plaintext_that_is_not_a_passport_backup(monkeypatch):
    fd = FakeFile()
    plaintext = bytearray(b'not a Passport backup')
    monkeypatch.setattr(builtins, 'open', lambda *_args, **_kwargs: fd)

    def invalid_plaintext(_fd, _password, _max_size, _progress_fcn):
        return 'passport-backup.txt', plaintext

    module, _calls = load_reader(monkeypatch, read_file=invalid_plaintext)

    assert module.read_backup_file('backup-code', 'backup.7z') == (None, Error.INVALID_BACKUP_CODE)
    assert plaintext == bytearray(len(plaintext))
    assert fd.closed


def test_classifies_card_removal_and_open_failures(monkeypatch):
    class MissingCardSlot:
        def __enter__(self):
            raise CardMissingError

        def __exit__(self, exc_type, exc_value, traceback):
            return False

    module, _calls = load_reader(monkeypatch, card_slot=MissingCardSlot)
    assert module.read_backup_file('backup-code', 'backup.7z') == (None, Error.MICROSD_CARD_MISSING)

    def fail_open(*_args, **_kwargs):
        raise OSError('open failed')

    monkeypatch.setattr(builtins, 'open', fail_open)
    module, _calls = load_reader(monkeypatch)
    assert module.read_backup_file('backup-code', 'backup.7z') == (None, Error.FILE_READ_ERROR)

    def fail_open_with_oom(*_args, **_kwargs):
        raise MemoryError

    monkeypatch.setattr(builtins, 'open', fail_open_with_oom)
    module, _calls = load_reader(monkeypatch)
    assert module.read_backup_file('backup-code', 'backup.7z') == (
        None, Error.OUT_OF_MEMORY_ERROR)


def test_close_failure_clears_plaintext(monkeypatch):
    plaintext = bytearray(b'# Passport backup\n')

    class CloseFailure(FakeFile):
        def close(self):
            raise OSError('close failed')

    def return_plaintext(_fd, _password, _max_size, _progress_fcn):
        return 'passport-backup.txt', plaintext

    monkeypatch.setattr(builtins, 'open', lambda *_args, **_kwargs: CloseFailure())
    module, _calls = load_reader(monkeypatch, read_file=return_plaintext)

    assert module.read_backup_file('backup-code', 'backup.7z') == (
        None, Error.FILE_READ_ERROR)
    assert plaintext == bytearray(len(plaintext))
