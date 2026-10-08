# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

import ast
import asyncio
import importlib.util
import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from test_wallet_policy import KEY_INFO, XPUB, StubChain
from policy_errors import PolicyParseError, PolicyResourceError
from policy_transport import decode_policy_transport
from wallet_policy import (KeyInfo, MAX_ORIGIN_DEPTH, MiniscriptPolicy,
                           POLICY_STORAGE_KEY)


MODULES = Path(__file__).resolve().parents[2]
ROOT = MODULES.parents[4]


def load_module(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def flow_method(filename, class_name, method_name):
    tree = ast.parse((MODULES / 'flows' / filename).read_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    method = next(node for node in cls.body if isinstance(node, ast.AsyncFunctionDef) and node.name == method_name)
    namespace = {}
    exec(compile(ast.Module(body=[method], type_ignores=[]), filename, 'exec'), namespace)
    return namespace[method_name]


def test_sparse_flash_partial_and_repeated_programming(tmp_path, monkeypatch):
    module = load_module(ROOT / 'simulator/sim_modules/constrained_sflash.py')
    monkeypatch.setattr(module, '_BACKING_FILE', str(tmp_path / 'flash.bin'))
    flash = module.SPIFlash()
    try:
        flash.write(17, b'\xf0\x55')
        page = bytearray(256)
        flash.read(0, page)
        assert page == b'\xff' * 17 + b'\xf0\x55' + b'\xff' * 237
        flash.write(17, b'\x0f\xff')
        flash.read(0, page)
        assert page[17:19] == b'\x00\x55'
        flash.sector_erase(0)
        flash.write(20, b'\xaa')
        flash.read(0, page)
        assert page == b'\xff' * 20 + b'\xaa' + b'\xff' * 235
    finally:
        flash._file.close()


def test_key_origin_depth_bound():
    at_limit = KeyInfo.parse('[6738736c' + '/0' * MAX_ORIGIN_DEPTH + ']' + XPUB)
    assert len(at_limit.path) == MAX_ORIGIN_DEPTH
    with pytest.raises(PolicyResourceError) as raised:
        KeyInfo.parse('[6738736c' + '/0' * (MAX_ORIGIN_DEPTH + 1) + ']' + XPUB)
    assert str(MAX_ORIGIN_DEPTH) in str(raised.value)


@pytest.mark.parametrize('field', ['name', 'network', 'template'])
@pytest.mark.parametrize('value', [None, 0, [], {}])
def test_transport_field_types_rejected_before_derivation(field, value):
    envelope = dict(format='passport-wallet-policy', version=1, name='Test', network='BTC',
                    template='wsh(pk(@0/**))', keys=[KEY_INFO])
    envelope[field] = value

    def derive(path):
        pytest.fail('Malformed transport reached key derivation')

    with pytest.raises(PolicyParseError):
        decode_policy_transport(json.dumps(envelope), StubChain(), 0, derive)


@pytest.mark.parametrize('compatible_sets,expected', [
    ([], 'could not be checked'),
    ([()], 'no spending path compatible'),
    ([(0,), ()], 'no spending path compatible'),
    ([(0,), (1,)], 'Inputs allow different spending paths'),
    ([(0,), (0,)], 'Spend now (1-of-1)'),
])
def test_authorization_preserves_path_results(monkeypatch, compatible_sets, expected):
    import policy_display
    policy = MiniscriptPolicy('Test', 'BTC', 'wsh(pk(@0/**))', (KEY_INFO,), (0,))
    monkeypatch.setattr(policy_display, 'compatible_path_indexes', lambda policy, version, lock, seq:
                        compatible_sets[seq])
    pages = []

    class Series:
        def __init__(self, page_type, args):
            pages.extend(arg['text'] for arg in args)

        async def run(self):
            return True

    monkeypatch.setitem(sys.modules, 'flows', SimpleNamespace(SeriesOfPagesFlow=Series))
    monkeypatch.setitem(sys.modules, 'pages', SimpleNamespace(LongTextPage=object))
    states = []
    flow = SimpleNamespace(psbt=SimpleNamespace(
        active_policy=policy, txn_version=2, lock_time=0,
        inputs=[SimpleNamespace(policy_spend_plan=SimpleNamespace(policy_id=policy.policy_id))
                for _ in compatible_sets],
        input_iter=lambda: enumerate(SimpleNamespace(nSequence=i) for i in range(len(compatible_sets)))),
        sign_transaction='sign', goto=states.append)
    asyncio.run(flow_method('sign_psbt_common_flow.py', 'SignPsbtCommonFlow', 'show_policy_authorization')(flow))
    assert expected in '\n'.join(pages)
    assert states == ['sign']
    if not compatible_sets or compatible_sets == [(0,), (1,)]:
        assert 'Policy Name' in '\n'.join(pages[1:])
    if any(not paths for paths in compatible_sets):
        assert 'Spend now (1-of-1)' not in '\n'.join(pages)


@pytest.mark.parametrize('task_name,args', [
    ('save_wallet_policy_task', ('policy',)),
    ('delete_wallet_policy_task', ('id',)),
    ('rename_wallet_policy_task', ('id', 'name')),
    ('rename_wallet_policy_keys_task', ('id', ['name'])),
])
@pytest.mark.parametrize('failure', ['capacity', 'io', 'callback'])
def test_policy_save_errors_and_success_callback(monkeypatch, task_name, args, failure):
    class SettingsOutOfSpace(Exception):
        pass

    original = ['original']
    current = list(original)
    saves = []

    def save():
        saves.append(list(current))
        if len(saves) == 1 and failure in ('capacity', 'io'):
            raise SettingsOutOfSpace() if failure == 'capacity' else OSError()

    def set_value(key, value):
        assert key == POLICY_STORAGE_KEY
        current[:] = value

    settings = SimpleNamespace(get=lambda key, default: current, set=set_value, save=save)

    class Registry:
        def __init__(self, settings):
            pass

        def get(self, policy_id):
            return None if failure == 'missing' else object()

        def change(self, *args):
            current[:] = ['changed']

        save = delete = rename = rename_keys = change

    errors = SimpleNamespace(USER_SETTINGS_FULL='full', USER_SETTINGS_SAVE_FAILED='failed')
    monkeypatch.setitem(sys.modules, 'common', SimpleNamespace(settings=settings))
    monkeypatch.setitem(sys.modules, 'errors', SimpleNamespace(Error=errors))
    monkeypatch.setitem(sys.modules, 'ext_settings', SimpleNamespace(SettingsOutOfSpace=SettingsOutOfSpace))
    import wallet_policy
    monkeypatch.setattr(wallet_policy, 'WalletPolicyRegistry', Registry)
    task = getattr(load_module(MODULES / 'tasks/wallet_policy_task.py'), task_name)
    results = []

    async def on_done(error):
        results.append(error)
        if failure == 'callback':
            raise RuntimeError('callback failed')

    if failure == 'callback':
        with pytest.raises(RuntimeError):
            asyncio.run(task(on_done, *args))
        assert current == ['changed']
        assert len(saves) == 1
        assert results == [None]
    else:
        asyncio.run(task(on_done, *args))
        assert current == original
        assert results == ['full' if failure == 'capacity' else 'failed']


def test_missing_policy_deletion_reports_save_failure(monkeypatch):
    test_policy_save_errors_and_success_callback(monkeypatch, 'delete_wallet_policy_task', ('id',), 'missing')


def test_microsd_import_bounds_read_before_decode(monkeypatch):
    data = io.BytesIO(b'x' * 8192)

    class Picker:
        def __init__(self, **kwargs):
            pass

        async def run(self):
            return 'policy', 'policy.txt', False

    async def spinner(label, task, args):
        path, binary, read_fn = args
        assert path == 'policy.txt' and binary
        return read_fn(data), None

    monkeypatch.setitem(sys.modules, 'flows', SimpleNamespace(FilePickerFlow=Picker))
    monkeypatch.setitem(sys.modules, 'tasks', SimpleNamespace(read_file_task=object()))
    monkeypatch.setitem(sys.modules, 'utils', SimpleNamespace(spinner_task=spinner))
    method = flow_method('wallet_policy_flow.py', 'ImportWalletPolicyFromMicroSDFlow', 'choose_file')

    def decode(value):
        assert len(value) == 4097
        assert data.tell() == 4097
        raise PolicyResourceError('too large')

    method.__globals__['_decode_policy'] = decode
    states = []
    flow = SimpleNamespace(show_error='error', goto=states.append)
    asyncio.run(method(flow))
    assert states == ['error']
    assert flow.error == 'too large'


@pytest.mark.parametrize('scan_result', ['qr-too-large', 'psbt-too-large'])
def test_qr_import_reports_microsd_fallback(monkeypatch, scan_result):
    class Scanner:
        def __init__(self, **kwargs):
            pass

        async def run(self):
            return scan_result

    monkeypatch.setitem(sys.modules, 'flows', SimpleNamespace(ScanQRFlow=Scanner))
    monkeypatch.setitem(sys.modules, 'data_codecs.qr_type', SimpleNamespace(QRType=SimpleNamespace(QR=1, UR2=2)))
    monkeypatch.setitem(sys.modules, 'foundation', SimpleNamespace(ur=SimpleNamespace(Value=SimpleNamespace(BYTES=1))))
    monkeypatch.setitem(sys.modules, 'errors', SimpleNamespace(Error=SimpleNamespace(
        QR_TOO_LARGE='qr-too-large', PSBT_OVERSIZED='psbt-too-large')))
    states = []
    flow = SimpleNamespace(show_error='error', goto=states.append)
    asyncio.run(flow_method('wallet_policy_flow.py', 'ImportWalletPolicyFromQRFlow', 'scan')(flow))
    assert states == ['error']
    assert 'microSD' in flow.error
