# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

import asyncio
import importlib.util
import os
import sys
import types


MODULES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TASK_PATH = os.path.join(MODULES_DIR, 'tasks', 'verify_backup_task.py')
sys.path.insert(1, MODULES_DIR)

from errors import Error


def load_task(monkeypatch, contents=b'# Passport backup\n', error=None):
    calls = []
    backup_reader = types.ModuleType('backup_reader')

    def read_backup_file(password, path):
        calls.append((password, path))
        return contents, error

    backup_reader.read_backup_file = read_backup_file
    monkeypatch.setitem(sys.modules, 'backup_reader', backup_reader)

    spec = importlib.util.spec_from_file_location('verify_backup_task_under_test', TASK_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.verify_backup_task, calls


def run_task(task):
    results = []

    async def on_done(error):
        results.append(error)

    asyncio.run(task(on_done, '1111-2222-3333-4444-5555', 'backup.7z'))
    return results


def test_success_reports_once_and_passes_credentials(monkeypatch):
    task, calls = load_task(monkeypatch)

    assert run_task(task) == [None]
    assert calls == [('1111-2222-3333-4444-5555', 'backup.7z')]


def test_each_reader_failure_reports_once(monkeypatch):
    errors = (
        Error.MICROSD_CARD_MISSING,
        Error.FILE_READ_ERROR,
        Error.INVALID_BACKUP_FILE_HEADER,
        Error.INVALID_BACKUP_CODE,
    )

    for error in errors:
        task, _calls = load_task(monkeypatch, contents=None, error=error)
        assert run_task(task) == [error]


def test_related_error_members_are_available():
    assert Error.MULTISIG_STORAGE_IDX_ERROR is not None
    assert Error.NOT_BIP39_MODE is not None
