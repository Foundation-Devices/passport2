# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

import asyncio
import builtins
import importlib.util
import os
import sys
import types


MODULES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TASK_PATH = os.path.join(MODULES_DIR, 'tasks', 'verify_backup_task.py')
sys.path.insert(1, MODULES_DIR)

from errors import Error


class CardMissingError(Exception):
    pass


class CardSlot:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


def load_task(monkeypatch, card_slot=CardSlot, check_headers=None, files=None):
    compat7z = types.ModuleType('compat7z')
    compat7z.check_file_headers = check_headers or (lambda _fd: None)

    class Builder:
        def verify_file_crc(self, _fd, _max_size):
            return files or [('passport-backup.txt', 1)]

    compat7z.Builder = Builder

    files_module = types.ModuleType('files')
    files_module.CardSlot = card_slot
    files_module.CardMissingError = CardMissingError

    constants = types.ModuleType('constants')
    constants.MAX_BACKUP_FILE_SIZE = 1024

    monkeypatch.setitem(sys.modules, 'compat7z', compat7z)
    monkeypatch.setitem(sys.modules, 'files', files_module)
    monkeypatch.setitem(sys.modules, 'constants', constants)

    spec = importlib.util.spec_from_file_location('verify_backup_task_under_test', TASK_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.verify_backup_task


def run_task(task):
    results = []

    async def on_done(error):
        results.append(error)

    asyncio.run(task(on_done, 'backup.7z'))
    return results


def test_success_reports_once(monkeypatch):
    fd = types.SimpleNamespace(close=lambda: None)
    monkeypatch.setattr(builtins, 'open', lambda *_args, **_kwargs: fd)

    assert run_task(load_task(monkeypatch)) == [None]


def test_card_removal_reports_once(monkeypatch):
    class MissingCardSlot:
        def __enter__(self):
            raise CardMissingError

        def __exit__(self, exc_type, exc_value, traceback):
            return False

    assert run_task(load_task(monkeypatch, card_slot=MissingCardSlot)) == [Error.MICROSD_CARD_MISSING]


def test_file_read_failure_reports_once(monkeypatch):
    def fail_open(*_args, **_kwargs):
        raise OSError('read failed')

    monkeypatch.setattr(builtins, 'open', fail_open)

    assert run_task(load_task(monkeypatch)) == [Error.FILE_READ_ERROR]


def test_invalid_header_reports_once(monkeypatch):
    fd = types.SimpleNamespace(close=lambda: None)
    monkeypatch.setattr(builtins, 'open', lambda *_args, **_kwargs: fd)

    def reject_header(_fd):
        raise ValueError('invalid header')

    assert run_task(load_task(monkeypatch, check_headers=reject_header)) == [Error.INVALID_BACKUP_FILE_HEADER]


def test_related_error_members_are_available():
    assert Error.MULTISIG_STORAGE_IDX_ERROR is not None
    assert Error.NOT_BIP39_MODE is not None
