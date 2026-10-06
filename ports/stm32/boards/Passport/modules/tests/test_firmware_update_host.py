# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Host tests: pytest ports/stm32/boards/Passport/modules/tests/test_firmware_update_host.py."""

import asyncio
import hashlib
import importlib.util
import os
from pathlib import Path
import shlex
import subprocess
import sys
from types import SimpleNamespace

import pytest

MODULES = Path(__file__).resolve().parents[1]
BOARD = MODULES.parent
HEADER_SIZE = 2048
ACTUAL_HEADER_SIZE = 170


def load_module(relative):
    spec = importlib.util.spec_from_file_location(Path(relative).stem, MODULES / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def environment(monkeypatch):
    class CardMissingError(Exception):
        pass

    class CardSlot:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    class Flash:
        def __init__(self):
            self.data = bytearray(b'\xff' * 16384)
            self.writes = []
            self.erases = []
            self.fail_at = None

        def is_busy(self):
            return False

        def sector_erase(self, address):
            self.erases.append(address)
            self.data[address:address + 4096] = b'\xff' * 4096

        def write(self, address, data):
            if address == self.fail_at:
                raise CardMissingError()
            self.writes.append(address)
            self.data[address:address + len(data)] = data

    def sha256(data, output):
        output[:] = hashlib.sha256(data).digest()

    async def sleep_ms(_):
        pass

    flash = Flash()
    errors = SimpleNamespace(FIRMWARE_UPDATE_FAILED=1, MICROSD_CARD_MISSING=2)
    device_hash = b'd' * 32
    system = SimpleNamespace(get_device_hash=lambda out: out.__setitem__(slice(None), device_hash))
    verified = []

    def verify_signatures(header, digest):
        verified.append((header, bytes(digest)))

    passport = SimpleNamespace(IS_SIMULATOR=False, InvalidFirmwareUpdate=ValueError,
                               verify_update_signatures=verify_signatures)
    stubs = {
        'constants': SimpleNamespace(FW_HEADER_SIZE=HEADER_SIZE, FW_ACTUAL_HEADER_SIZE=ACTUAL_HEADER_SIZE,
                                     FW_HEADER_INFORMATION_SIZE=34),
        'trezorcrypto': SimpleNamespace(sha256=hashlib.sha256),
        'foundation': SimpleNamespace(sha256=sha256),
        'passport': passport,
        'uasyncio': SimpleNamespace(sleep_ms=sleep_ms),
        'ubinascii': __import__('binascii'),
        'files': SimpleNamespace(CardSlot=CardSlot, CardMissingError=CardMissingError),
        'errors': SimpleNamespace(Error=errors),
        'common': SimpleNamespace(system=system, sf=flash),
    }
    for name, value in stubs.items():
        monkeypatch.setitem(sys.modules, name, value)
    return SimpleNamespace(flash=flash, errors=errors, verified=verified, device_hash=device_hash)


def run_task(relative, function, path, size, header, progress=lambda _: None):
    results = []

    async def done(error, message):
        results.append((error, message))

    module = load_module(relative)
    module.open = lambda file, mode: open(file, mode, buffering=0)
    asyncio.run(getattr(module, function)(str(path), size, header, progress, done))
    return results


@pytest.mark.parametrize('task', ['verify_firmware_signature_task', 'copy_firmware_to_spi_flash_task'])
def test_changed_header_rejected_before_staging(environment, tmp_path, task):
    expected = bytes(HEADER_SIZE)
    changed = bytearray(expected)
    changed[102] = 1  # Second public key index in the serialized header.
    path = tmp_path / 'firmware.bin'
    path.write_bytes(changed + bytes(2048))
    results = run_task('tasks/' + task + '.py', task, path, 4096, expected)
    assert len(results) == 1 and results[0][0] == environment.errors.FIRMWARE_UPDATE_FAILED
    assert not environment.flash.erases
    assert not environment.flash.writes
    assert not environment.verified


def test_checked_header_is_staged_without_rereading(environment, tmp_path):
    header = bytes(HEADER_SIZE)
    body = bytes(range(256)) * 9 + b'last'
    image = header + body
    path = tmp_path / 'firmware.bin'
    path.write_bytes(image)
    verify = 'verify_firmware_signature_task'
    assert run_task('tasks/' + verify + '.py', verify, path, len(image), header) == [(None, None)]
    assert environment.verified == [(header, hashlib.sha256(hashlib.sha256(header[:34] + body).digest()).digest())]

    def change_source(_):
        with path.open('r+b') as fp:
            fp.seek(102)
            fp.write(b'\x01')

    copy = 'copy_firmware_to_spi_flash_task'
    assert run_task('tasks/' + copy + '.py', copy, path, len(image), header, change_source) == [(None, None)]
    assert environment.flash.data[256:256 + len(image)] == image
    assert environment.flash.writes[-1] == 0
    header_hash = hashlib.sha256(hashlib.sha256(header[:ACTUAL_HEADER_SIZE]).digest()).digest()
    assert environment.flash.data[:32] == hashlib.sha256(header_hash + environment.device_hash).digest()


@pytest.mark.parametrize('task', ['verify_firmware_signature_task', 'copy_firmware_to_spi_flash_task'])
def test_truncated_body_fails_once(environment, tmp_path, task):
    header = bytes(HEADER_SIZE)
    path = tmp_path / 'firmware.bin'
    path.write_bytes(header + b'short')
    results = run_task('tasks/' + task + '.py', task, path, 4096, header)
    assert len(results) == 1 and results[0][0] == environment.errors.FIRMWARE_UPDATE_FAILED
    assert 0 not in environment.flash.writes
    assert not environment.verified


def test_copy_failure_never_authorizes_update(environment, tmp_path):
    header = bytes(HEADER_SIZE)
    path = tmp_path / 'firmware.bin'
    path.write_bytes(header + bytes(2048))
    environment.flash.fail_at = 512
    task = 'copy_firmware_to_spi_flash_task'
    results = run_task('tasks/' + task + '.py', task, path, 4096, header)
    assert results == [(environment.errors.MICROSD_CARD_MISSING, None)]
    assert 0 not in environment.flash.writes


def test_installed_firmware_detection_c(tmp_path):
    harness = tmp_path / 'detection.c'
    source = (BOARD / 'bootloader/update.c').read_text()
    start = source.index('secresult is_user_signed_firmware_installed(void) {')
    detection = source[start:source.index('\n}', start) + 2]
    harness.write_text('''
#include <assert.h>
#include "secresult.h"
#include "firmware-classification.h"
static passport_firmware_header_t installed;
#define BL_FW_HDR_BASE (&installed)
''' + detection + '''

int main(void) {
    const uint32_t second_keys[] = {0, 1, 2, FW_MAX_PUB_KEYS, UINT32_MAX};
    for (unsigned int i = 0; i < sizeof(second_keys) / sizeof(second_keys[0]); i++) {
        installed.signature.pubkey2 = second_keys[i];
        installed.signature.pubkey1 = FW_USER_KEY;
        assert(firmware_is_user_signed(&installed));
        assert(is_user_signed_firmware_installed() == SEC_TRUE);
        for (uint32_t key = 0; key < FW_MAX_PUB_KEYS; key++) {
            installed.signature.pubkey1 = key;
            assert(!firmware_is_user_signed(&installed));
            assert(is_user_signed_firmware_installed() == SEC_FALSE);
        }
    }
}
''')
    binary = tmp_path / 'detection'
    subprocess.run(shlex.split(os.environ.get('CC', 'cc')) +
                   ['-std=c11', '-I', str(BOARD / 'include'), str(harness), '-o', str(binary)], check=True)
    subprocess.run([str(binary)], check=True)


@pytest.mark.parametrize('screen', ['COLOR', 'MONO'])
def test_bootloader_header_validation_c(tmp_path, screen):
    source = (BOARD / 'bootloader/verify.c').read_text()
    start = source.index('secresult verify_header(')
    validation = source[start:source.index('\n}', start) + 2]
    harness = tmp_path / 'header.c'
    harness.write_text('''
#include <assert.h>
#include <stddef.h>
#include "firmware-classification.h"
#include "secresult.h"
''' + validation + '''
int main(void) {
    passport_firmware_header_t header = {0};
#ifdef SCREEN_MODE_COLOR
    header.info.magic = FW_HEADER_MAGIC_COLOR;
#else
    header.info.magic = FW_HEADER_MAGIC;
#endif
    header.info.timestamp = 1;
    header.info.fwversion[0] = '1';
    header.info.fwlength = FW_HEADER_SIZE;
    header.signature.pubkey1 = FW_USER_KEY;
    header.signature.signature1[0] = 1;
    assert(verify_header(&header) == SEC_TRUE);

    const uint32_t second_keys[] = {1, FW_MAX_PUB_KEYS, FW_USER_KEY, UINT32_MAX};
    for (size_t i = 0; i < sizeof(second_keys) / sizeof(second_keys[0]); i++) {
        header.signature.pubkey2 = second_keys[i];
        assert(verify_header(&header) == SEC_FALSE);
    }
    header.signature.pubkey2 = 0;
    for (size_t i = 0; i < sizeof(header.signature.signature2); i++) {
        header.signature.signature2[i] = 1;
        assert(verify_header(&header) == SEC_FALSE);
        header.signature.signature2[i] = 0;
    }
    assert(verify_header(&header) == SEC_TRUE);

    header.signature.signature2[0] = 1;
    for (uint32_t first = 0; first < FW_MAX_PUB_KEYS; first++) {
        for (uint32_t second = 0; second < FW_MAX_PUB_KEYS; second++) {
            if (first == second) continue;
            header.signature.pubkey1 = first;
            header.signature.pubkey2 = second;
            assert(verify_header(&header) == SEC_TRUE);
        }
    }
}
''')
    binary = tmp_path / 'header'
    subprocess.run(shlex.split(os.environ.get('CC', 'cc')) +
                   ['-std=c11', '-D', 'SCREEN_MODE_' + screen, '-I', str(BOARD / 'include'),
                    str(harness), '-o', str(binary)], check=True)
    subprocess.run([str(binary)], check=True)


@pytest.mark.parametrize('developer', [True, False])
def test_key_removal_guard(monkeypatch, developer):
    events = []

    class Flow:
        def __init__(self, initial_state):
            pass

        def set_result(self, result):
            events.append(('result', result))

        def goto(self, state):
            events.append(('goto', state.__name__))

    class Page:
        def __init__(self, *args, **kwargs):
            pass

        async def show(self):
            events.append(('page', None))
            return True

    system = SimpleNamespace(is_user_firmware_installed=lambda: developer,
                             set_user_firmware_pubkey=lambda key: events.append(('clear', key)))
    for name, stub in {
        'flows': SimpleNamespace(Flow=Flow),
        'pages': SimpleNamespace(SuccessPage=Page, ErrorPage=Page, QuestionPage=Page),
        'utils': SimpleNamespace(clear_cached_pubkey=lambda: events.append(('cache', None))),
        'common': SimpleNamespace(system=system),
    }.items():
        monkeypatch.setitem(sys.modules, name, stub)
    flow = load_module('flows/remove_dev_pubkey_flow.py').RemoveDevPubkeyFlow()
    asyncio.run(flow.check_for_user_signed_firmware())
    if developer:
        assert events == [('page', None), ('result', True)]
    else:
        assert events == [('goto', 'remove_dev_pubkey')]


def test_update_flow_passes_selected_header_to_both_tasks(monkeypatch):
    calls = []
    pending = []

    class Flow:
        def __init__(self, **kwargs):
            pass

        def goto(self, state):
            calls.append(state.__name__)

        def set_result(self, result):
            calls.append(result)

    class ProgressPage:
        def __init__(self, **kwargs):
            self.result = None

        def set_progress(self, percent):
            pass

        def set_result(self, result):
            self.result = result

        async def show(self):
            await pending.pop()
            return self.result

    async def verify(path, size, header, progress, done):
        calls.append(('verify', header))
        await done(None, None)

    async def copy(path, size, header, progress, done):
        calls.append(('copy', header))
        await done(None, None)

    page_names = ['ErrorPage', 'ProgressPage', 'QuestionPage', 'SuccessPage', 'InsertMicroSDPage', 'InfoPage']
    pages = {name: ProgressPage for name in page_names}
    stubs = {
        'lvgl': SimpleNamespace(),
        'machine': SimpleNamespace(),
        'files': SimpleNamespace(CardSlot=None),
        'constants': SimpleNamespace(FW_HEADER_SIZE=HEADER_SIZE, FW_MAX_SIZE=2000000),
        'pages': SimpleNamespace(**pages),
        'tasks': SimpleNamespace(verify_firmware_signature_task=verify, copy_firmware_to_spi_flash_task=copy),
        'flows': SimpleNamespace(Flow=Flow, FilePickerFlow=None),
        'utils': SimpleNamespace(read_user_firmware_pubkey=None, is_all_zero=None, start_task=pending.append),
        'errors': SimpleNamespace(Error=None),
        'passport': SimpleNamespace(),
        'common': SimpleNamespace(ui=SimpleNamespace(set_is_top_level=lambda value: True),
                                  system=SimpleNamespace(get_software_info=lambda: ('2.4.0', 0, 0, True, '')),
                                  settings=SimpleNamespace(set=lambda *args: None, save=lambda: None)),
    }
    for name, value in stubs.items():
        monkeypatch.setitem(sys.modules, name, value)
    flow = load_module('flows/update_firmware_flow.py').UpdateFirmwareFlow(reset_after=False)
    header = bytes(HEADER_SIZE)
    flow.update_header = header
    flow.update_file_path = 'firmware.bin'
    flow.size = 4096
    flow.version = '2.4.0'
    asyncio.run(flow.verify_firmware_signature())
    asyncio.run(flow.copy_to_flash())
    assert calls == [('verify', header), 'copy_to_flash', ('copy', header), True]
