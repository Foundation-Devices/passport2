# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

import asyncio
import importlib.util
import os
import sys
import types

import pytest


MODULES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
FLOW_PATH = os.path.join(MODULES_DIR, 'flows', 'verify_backup_flow.py')
sys.path.insert(1, MODULES_DIR)

from errors import Error


class Flow:
    def __init__(self, initial_state, name):
        self.initial_state = initial_state
        self.name = name
        self.next_state = None
        self.result = None
        self.went_back = False

    def goto(self, state):
        self.next_state = state

    def back(self):
        self.went_back = True

    def set_result(self, result):
        self.result = result


class FilePickerFlow:
    def __init__(self, **_kwargs):
        pass


class FakePage:
    shown = []
    result = None

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    async def show(self):
        type(self).shown.append(self.kwargs)
        return type(self).result


class BackupCodePage(FakePage):
    pass


class ErrorPage(FakePage):
    pass


class InsertMicroSDPage(FakePage):
    pass


class LongSuccessPage(FakePage):
    pass


class SuccessPage(FakePage):
    pass


def load_flow(monkeypatch, is_color, spinner_error=None):
    for page in (BackupCodePage, ErrorPage, InsertMicroSDPage, LongSuccessPage, SuccessPage):
        page.shown = []
        page.result = None

    constants = types.ModuleType('constants')
    constants.TOTAL_BACKUP_CODE_DIGITS = 20

    flows = types.ModuleType('flows')
    flows.Flow = Flow
    flows.FilePickerFlow = FilePickerFlow

    pages = types.ModuleType('pages')
    pages.BackupCodePage = BackupCodePage
    pages.ErrorPage = ErrorPage
    pages.InsertMicroSDPage = InsertMicroSDPage
    pages.LongSuccessPage = LongSuccessPage
    pages.SuccessPage = SuccessPage

    spinner_calls = []
    utils = types.ModuleType('utils')
    utils.get_backup_code_as_password = lambda digits: ''.join(str(digit) for digit in digits)
    utils.get_backups_folder_path = lambda: '/backups'

    async def spinner_task(title, task, args):
        spinner_calls.append((title, task, args))
        return (spinner_error,)

    utils.spinner_task = spinner_task

    tasks = types.ModuleType('tasks')
    tasks.verify_backup_task = object()

    microns = types.ModuleType('microns')
    microns.Back = object()
    microns.Retry = object()

    passport = types.ModuleType('passport')
    passport.IS_COLOR = is_color

    monkeypatch.setitem(sys.modules, 'constants', constants)
    monkeypatch.setitem(sys.modules, 'flows', flows)
    monkeypatch.setitem(sys.modules, 'pages', pages)
    monkeypatch.setitem(sys.modules, 'utils', utils)
    monkeypatch.setitem(sys.modules, 'tasks', tasks)
    monkeypatch.setitem(sys.modules, 'microns', microns)
    monkeypatch.setitem(sys.modules, 'passport', passport)

    spec = importlib.util.spec_from_file_location('verify_backup_flow_under_test', FLOW_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.VerifyBackupFlow(), spinner_calls, tasks.verify_backup_task


def run(coroutine):
    asyncio.run(coroutine)


def test_enters_backup_code_before_verification(monkeypatch):
    flow, _spinner_calls, _task = load_flow(monkeypatch, is_color=True)
    digits = list(range(10)) * 2
    BackupCodePage.result = digits

    run(flow.enter_backup_code())

    assert flow.backup_code == digits
    assert flow.decryption_password == ''.join(str(digit) for digit in digits)
    assert flow.next_state == flow.do_verify


@pytest.mark.parametrize(
    ('is_color', 'success_page'),
    ((True, SuccessPage), (False, LongSuccessPage)))
def test_success_requires_decryption_on_both_screen_variants(
        monkeypatch, is_color, success_page):
    flow, spinner_calls, task = load_flow(monkeypatch, is_color=is_color)
    flow.backup_file_path = '/backups/backup.7z'
    flow.decryption_password = 'backup-code'
    flow.backup_code = [1] * 20

    run(flow.do_verify())

    assert spinner_calls == [(
        'Verifying Backup',
        task,
        ['backup-code', '/backups/backup.7z'])]
    assert success_page.shown == [{
        'text': 'Backup decrypted successfully and passed its integrity check.'}]
    assert flow.backup_code == [None] * 20
    assert flow.decryption_password is None
    assert flow.result is True


def test_integrity_failure_returns_to_code_entry_without_leaking_detail(monkeypatch):
    flow, _spinner_calls, _task = load_flow(
        monkeypatch, is_color=True, spinner_error=Error.INVALID_BACKUP_CODE)
    flow.backup_file_path = '/backups/backup.7z'
    flow.decryption_password = 'backup-code'
    flow.backup_code = [1] * 20
    ErrorPage.result = True

    run(flow.do_verify())

    assert ErrorPage.shown == [{
        'text': 'Unable to decrypt backup. The Backup Code may be incorrect, '
                'or the backup may be damaged.',
        'left_micron': sys.modules['microns'].Back,
        'right_micron': sys.modules['microns'].Retry,
    }]
    assert flow.decryption_password is None
    assert flow.backup_code == [1] * 20
    assert flow.went_back
    assert flow.result is None


def test_card_cancel_clears_backup_code_and_exits(monkeypatch):
    flow, _spinner_calls, _task = load_flow(
        monkeypatch, is_color=True, spinner_error=Error.MICROSD_CARD_MISSING)
    flow.backup_file_path = '/backups/backup.7z'
    flow.decryption_password = 'backup-code'
    flow.backup_code = [1] * 20
    InsertMicroSDPage.result = False

    run(flow.do_verify())

    assert flow.backup_code == [None] * 20
    assert flow.decryption_password is None
    assert flow.result is False
