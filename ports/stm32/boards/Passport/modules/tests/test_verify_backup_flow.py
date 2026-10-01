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
        self.state = initial_state
        self.prev_states = []
        self.name = name
        self.result = None
        self.went_back = False

    def goto(self, state):
        self.prev_states.append(self.state)
        self.state = state

    def back(self):
        self.went_back = True
        self.state = self.prev_states.pop()

    def set_result(self, result):
        self.result = result


class FilePickerFlow:
    result = None

    def __init__(self, **_kwargs):
        pass

    async def run(self):
        return type(self).result


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


class RecoveryModeChooserPage(FakePage):
    pass


class PredictiveTextInputPage(FakePage):
    pass


class QuestionPage(FakePage):
    pass


class RecoveryMode:
    BACKUP_CODE_20_DIGITS = 0
    BACKUP_PASSWORD_6_WORDS = 1


class ErrorPage(FakePage):
    pass


class InsertMicroSDPage(FakePage):
    pass


class LongSuccessPage(FakePage):
    pass


class SuccessPage(FakePage):
    pass


def load_flow(monkeypatch, is_color, spinner_error=None):
    for page in (BackupCodePage, ErrorPage, InsertMicroSDPage, LongSuccessPage, SuccessPage,
                 RecoveryModeChooserPage, PredictiveTextInputPage, QuestionPage):
        page.shown = []
        page.result = None
    FilePickerFlow.result = None

    constants = types.ModuleType('constants')
    constants.TOTAL_BACKUP_CODE_DIGITS = 20
    constants.NUM_BACKUP_PASSWORD_WORDS = 6

    flows = types.ModuleType('flows')
    flows.Flow = Flow
    flows.FilePickerFlow = FilePickerFlow

    pages = types.ModuleType('pages')
    pages.BackupCodePage = BackupCodePage
    pages.ErrorPage = ErrorPage
    pages.InsertMicroSDPage = InsertMicroSDPage
    pages.LongSuccessPage = LongSuccessPage
    pages.SuccessPage = SuccessPage
    pages.RecoveryModeChooserPage = RecoveryModeChooserPage
    pages.PredictiveTextInputPage = PredictiveTextInputPage
    pages.QuestionPage = QuestionPage
    recovery_mode = types.ModuleType('pages.recovery_mode_chooser_page')
    recovery_mode.RecoveryMode = RecoveryMode
    monkeypatch.setitem(sys.modules, 'pages.recovery_mode_chooser_page', recovery_mode)

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


def test_selected_file_routes_through_backup_code_before_verification(monkeypatch):
    flow, _spinner_calls, _task = load_flow(monkeypatch, is_color=True)
    digits = list(range(10)) * 2
    FilePickerFlow.result = ('backup.7z', '/backups/backup.7z', False)
    BackupCodePage.result = digits
    RecoveryModeChooserPage.result = RecoveryMode.BACKUP_CODE_20_DIGITS

    run(flow.state())
    assert flow.state == flow.select_recovery_mode
    run(flow.state())
    assert flow.state == flow.enter_backup_code

    run(flow.state())

    assert flow.backup_code == digits
    assert flow.decryption_password == ''.join(str(digit) for digit in digits)
    assert flow.state == flow.do_verify


def test_selecting_folder_does_not_advance_to_code_entry(monkeypatch):
    flow, _spinner_calls, _task = load_flow(monkeypatch, is_color=True)
    FilePickerFlow.result = ('backups', '/backups', True)

    run(flow.state())

    assert flow.state == flow.choose_file
    assert flow.result is None


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
    flow.state = flow.do_verify
    flow.prev_states = [flow.choose_file, flow.enter_backup_code]
    ErrorPage.result = True

    run(flow.do_verify())

    assert ErrorPage.shown == [{
        'text': 'Unable to decrypt backup. The Backup Code or password may be incorrect, '
                'or the backup may be damaged.',
        'left_micron': sys.modules['microns'].Back,
        'right_micron': sys.modules['microns'].Retry,
    }]
    assert flow.decryption_password is None
    assert flow.backup_code == [1] * 20
    assert flow.went_back
    assert flow.state == flow.enter_backup_code
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


@pytest.mark.parametrize('is_color', [True, False])
@pytest.mark.parametrize('legacy', [True, False])
def test_both_credentials_verify_and_clear_on_both_screens(monkeypatch, is_color, legacy):
    flow, calls, _task = load_flow(monkeypatch, is_color=is_color)
    FilePickerFlow.result = ('backup.7z', '/backups/backup.7z', False)
    words = ['able', 'acid', 'also', 'apex', 'aqua', 'arch']
    RecoveryModeChooserPage.result = (
        RecoveryMode.BACKUP_PASSWORD_6_WORDS if legacy else RecoveryMode.BACKUP_CODE_20_DIGITS)
    PredictiveTextInputPage.result = (words, ['a'] * 6, None)
    BackupCodePage.result = [1] * 20
    for _ in range(4):
        run(flow.state())
    assert calls[0][2] == [' '.join(words) if legacy else '1' * 20, '/backups/backup.7z']
    assert flow.result is True
    assert flow.backup_password_words == []
    assert flow.backup_password_prefixes == []
    assert flow.backup_code == [None] * 20
    assert flow.decryption_password is None


def test_legacy_retry_returns_to_password_entry(monkeypatch):
    flow, _calls, _task = load_flow(monkeypatch, is_color=True, spinner_error=Error.INVALID_BACKUP_CODE)
    FilePickerFlow.result = ('backup.7z', '/backups/backup.7z', False)
    RecoveryModeChooserPage.result = RecoveryMode.BACKUP_PASSWORD_6_WORDS
    words = ['able'] * 6
    PredictiveTextInputPage.result = (words, ['a'] * 6, None)
    ErrorPage.result = True
    for _ in range(4):
        run(flow.state())
    assert flow.state == flow.enter_backup_password
    assert flow.backup_password_words == words
    assert flow.decryption_password is None


@pytest.mark.parametrize('cancel', [True, False])
def test_legacy_entry_cancellation(monkeypatch, cancel):
    flow, _calls, _task = load_flow(monkeypatch, is_color=True)
    flow.state = flow.enter_backup_password
    flow.prev_states = [flow.choose_file, flow.select_recovery_mode]
    flow.backup_password_words = ['able'] * 6
    PredictiveTextInputPage.result = (None, ['a'] * 6, None)
    QuestionPage.result = cancel
    run(flow.state())
    assert flow.state == (flow.select_recovery_mode if cancel else flow.enter_backup_password)
    assert flow.backup_password_words == ([] if cancel else ['able'] * 6)
    assert flow.backup_password_prefixes == ([] if cancel else ['a'] * 6)


@pytest.mark.parametrize('error', [
    Error.INVALID_BACKUP_CODE, Error.FILE_READ_ERROR,
    Error.INVALID_BACKUP_FILE_HEADER, Error.MICROSD_CARD_MISSING,
    Error.OUT_OF_MEMORY_ERROR])
def test_terminal_failure_clears_legacy_credentials(monkeypatch, error):
    flow, _calls, _task = load_flow(monkeypatch, is_color=True, spinner_error=error)
    flow.backup_file_path = '/backups/backup.7z'
    flow.backup_password_words = ['able'] * 6
    flow.backup_password_prefixes = ['a'] * 6
    flow.decryption_password = ' '.join(flow.backup_password_words)
    run(flow.do_verify())
    assert flow.result is False
    assert flow.backup_password_words == []
    assert flow.backup_password_prefixes == []
    assert flow.decryption_password is None


@pytest.mark.parametrize(
    ('error', 'message'),
    (
        (Error.OUT_OF_MEMORY_ERROR, 'Not enough memory to verify this backup.'),
        (object(), 'Unable to verify backup.'),
    ))
def test_unexpected_and_out_of_memory_errors_are_terminal(monkeypatch, error, message):
    flow, _spinner_calls, _task = load_flow(
        monkeypatch, is_color=True, spinner_error=error)
    flow.backup_file_path = '/backups/backup.7z'
    flow.decryption_password = 'backup-code'
    flow.backup_code = [1] * 20

    run(flow.do_verify())

    assert ErrorPage.shown == [{'text': message}]
    assert flow.backup_code == [None] * 20
    assert flow.decryption_password is None
    assert flow.result is False
