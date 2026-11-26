# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

"""SFT-974 review regressions; assertions describe the required behavior.

Run with the other host tests. Hardware/UI adapters are replaced, while the
policy parser, output validator and signing task are the production code.
All keys are derived from synthetic, public test seeds.
"""

import ast
import asyncio
import base64
import builtins
import collections
import hashlib
import io
import runpy
import struct
import sys
import types
from pathlib import Path

import pytest
from embit import bip32, ec, script


MODULES = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(MODULES)) if str(MODULES) not in sys.path else None


def test_keys(count):
    result = []
    for index in range(count):
        root = bip32.HDKey.from_seed(bytes([index + 1]) * 32)
        account = root.derive("m/48h/0h/0h/2h").to_public()
        result.append("[{} /48'/0'/0'/2']{}".format(
            root.my_fingerprint.hex(), account.to_base58()).replace(' ', ''))
    return result


test_keys.__test__ = False


@pytest.fixture
def psbt_module(monkeypatch):
    """Load actual PSBT code with only platform dependencies adapted."""
    monkeypatch.setattr(builtins, 'const', lambda value: value, raising=False)

    def module(name, **attrs):
        value = types.ModuleType(name)
        value.__dict__.update(attrs)
        monkeypatch.setitem(sys.modules, name, value)
        return value

    for name, value in (('ustruct', struct), ('uio', io),
                        ('ucollections', collections)):
        monkeypatch.setitem(sys.modules, name, value)
    import binascii
    monkeypatch.setitem(sys.modules, 'ubinascii', binascii)
    module('trezorcrypto', sha256=hashlib.sha256,
           ripemd160=lambda data: hashlib.new('ripemd160', data))
    module('utils', xfp2str=lambda value: value.to_bytes(4, 'little').hex(),
           B2A=lambda value: value.hex(), bytes_to_hex_str=lambda value: value.hex(),
           keypath_to_str=lambda value: tuple(value), swab32=lambda value: value,
           get_accounts_by_xfp=None, get_derived_keys=None)
    module('chains')
    module('common')
    module('history', verify_amount=lambda *args: None,
           OutptValueCache=types.SimpleNamespace(record_amounts=lambda entries: list(entries)))
    module('sffile', SizerFile=object)
    module('passport', mem=types.SimpleNamespace())
    module('constants', PSBT_MAX_SIZE=1024 * 1024)
    module('multisig_wallet', MultisigWallet=object,
           disassemble_multisig_mn=lambda _: (1, 2))
    module('taproot', output_script=lambda *args: b'', tagged_hash=lambda *args: b'')
    for name in ('public_constants', 'serializations', 'exceptions'):
        loaded = module(name)
        loaded.__dict__.update(runpy.run_path(str(MODULES / (name + '.py'))))
    wallet_utils = module('wallets.utils')
    wallet_utils.__dict__.update(runpy.run_path(str(MODULES / 'wallets/utils.py')))
    return types.SimpleNamespace(**runpy.run_path(str(MODULES / 'psbt.py')))


@pytest.mark.parametrize('output_kind', ['p2pkh', 'p2wpkh', 'p2sh-p2wpkh'])
@pytest.mark.parametrize('registered_policy', [True, False])
@pytest.mark.parametrize('derivation_kind', ['policy', 'singlesig'])
def test_policy_funds_sent_to_singlesig_are_not_hidden_as_change(
        monkeypatch, psbt_module, output_kind, registered_policy, derivation_kind):
    from wallet_policy import MiniscriptPolicy
    policy = MiniscriptPolicy('Two signers', 'BTC',
                              'wsh(multi(2,@0/**,@1/**))', test_keys(2), (0,))
    root = bip32.HDKey.from_seed(bytes([1]) * 32)
    if derivation_kind == 'policy':
        derivation = bip32.parse_path('m/48h/0h/0h/2h/1/7')
    else:
        purpose = {'p2pkh': 44, 'p2wpkh': 84, 'p2sh-p2wpkh': 49}[output_kind]
        derivation = bip32.parse_path('m/{}h/0h/0h/1/7'.format(purpose))
    child = root.derive(derivation)
    pubkey = child.get_public_key()
    xfp = int.from_bytes(root.my_fingerprint, 'little')
    path = [xfp] + derivation
    redeem_script = script.p2wpkh(pubkey).data if output_kind == 'p2sh-p2wpkh' else b''
    output_script = script.p2sh(script.Script(redeem_script)).data if redeem_script else \
        getattr(script, output_kind)(pubkey).data
    txo = sys.modules['serializations'].CTxOut(10000, output_script)
    output = psbt_module.psbtOutputProxy(io.BytesIO(b'\x00'), 0)
    # Exercise the production derivation decoder using its file-offset values.
    derivation_bytes = struct.pack('<{}I'.format(len(path)), *path)
    output.fd = io.BytesIO(derivation_bytes + redeem_script)
    output.subpaths = {pubkey.sec(): (0, len(derivation_bytes))}
    if redeem_script:
        output.redeem_script = (len(derivation_bytes), len(redeem_script))
    output.validate(0, txo, xfp, None, policy if registered_policy else None)
    # The final ownership check also passes: this really is Passport's key,
    # but the output has removed the other signer's authorization requirement.

    class Values:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def derive_path(self, path):
            return types.SimpleNamespace(public_key=lambda: pubkey.sec())

    monkeypatch.setitem(sys.modules, 'stash', types.SimpleNamespace(SensitiveValues=Values))
    monkeypatch.setitem(sys.modules, 'errors', types.SimpleNamespace(Error=object))
    results = []

    async def done(message, code):
        results.append((message, code))

    check = runpy.run_path(str(MODULES / 'tasks/double_check_psbt_change_task.py'))[
        'double_check_psbt_change_task']
    asyncio.run(check(done, types.SimpleNamespace(outputs=[output], my_xfp=xfp)))
    assert results == [(None, None)]
    if registered_policy or derivation_kind == 'policy':
        assert not output.is_change, 'An output outside the registered policy must be displayed'
    else:
        assert output.is_change, 'Ordinary singlesig change must still be recognized'


def test_nested_optional_timelock_does_not_hide_immediate_authorization():
    from wallet_policy import MiniscriptPolicy
    from policy_display import compatible_path_indexes, policy_paths
    policy = MiniscriptPolicy(
        'Nested alternatives', 'BTC',
        'wsh(or_i(and_v(v:pk(@0/**),or_i(pk(@1/**),'
        'and_v(v:pk(@2/**),older(10)))),pk(@3/**)))', test_keys(4), (0,))
    paths = policy_paths(policy)
    compatible = compatible_path_indexes(policy, 2, 0, 0xffffffff)
    # Passport + key 1 satisfy the first outer branch without executing CSV.
    assert any(0 in paths[index]['keys'] for index in compatible), (
        'A satisfiable Passport authorization disappeared from the signing review: ' +
        repr(policy.format_signing_pages(compatible)))


@pytest.fixture
def multi_policy_input(monkeypatch, psbt_module):
    from wallet_policy import MiniscriptPolicy

    class Node:
        def __init__(self, xpub):
            self.node = bip32.HDKey.from_base58(xpub)

        def depth(self):
            return self.node.depth

        def derive(self, index, public=False):
            self.node = self.node.child(index)

        def public_key(self):
            return self.node.get_public_key().sec()

    chain = types.SimpleNamespace(
        ctype='BTC', deserialize_node=lambda xpub, fmt: Node(xpub),
        p2sh_address=lambda fmt, witness: script.p2wsh(script.Script(witness)).address())
    monkeypatch.setitem(sys.modules, 'chains', types.SimpleNamespace(current_chain=lambda: chain))
    policy = MiniscriptPolicy('Registered multi', 'BTC',
                              'wsh(multi(2,@0/**,@1/**))', test_keys(2), (0,))
    derived, paths, _ = policy._derive_with_paths(0, 7, chain)
    settings = {'wallet_policies': [policy.serialize()]}
    monkeypatch.setitem(sys.modules, 'common', types.SimpleNamespace(settings=settings))
    xfp = int.from_bytes(bytes.fromhex(policy.keys[0].fingerprint), 'little')

    def make_input(registered=True, include_global_xpubs=True):
        settings['wallet_policies'] = [policy.serialize()] if registered else []
        inp = psbt_module.psbtInputProxy(io.BytesIO(b'\x00'), 0)
        inp.fd = io.BytesIO(derived.witness_script)
        inp.witness_script = (0, len(derived.witness_script))
        inp.subpaths = paths
        inp.sighash = 1
        psbt = object.__new__(psbt_module.psbtObject)
        psbt.inputs = [inp]
        psbt.my_xfp = xfp
        psbt.active_policy = None
        psbt.active_multisig = None
        psbt.multisig_import_needs_approval = False
        psbt.xpubs = {(struct.pack('<5I', int.from_bytes(bytes.fromhex(key.fingerprint), 'little'),
                                   *key.path), bytes([index])): None
                      for index, key in enumerate(policy.keys)} if include_global_xpubs else {}
        txo = sys.modules['serializations'].CTxOut(10000, derived.script_pubkey)
        return psbt, inp, txo

    return policy, make_input


@pytest.mark.parametrize('include_global_xpubs', [False, True])
def test_registered_multi_policy_is_not_preempted_by_global_xpubs(
        monkeypatch, psbt_module, multi_policy_input, include_global_xpubs):
    policy, make_input = multi_policy_input
    psbt, inp, txo = make_input(include_global_xpubs=include_global_xpubs)

    def forbidden_discovery(*args):
        pytest.fail('Registered policy triggered legacy discovery/import')

    monkeypatch.setitem(psbt_module.psbtObject.handle_xpubs.__globals__, 'MultisigWallet',
                        types.SimpleNamespace(find_candidates=forbidden_discovery,
                                              import_from_psbt=forbidden_discovery))
    # Exercise initial validation too: it must not activate a wallet from
    # global metadata before the real per-input policy matcher gets a turn.
    psbt.txn = (0, 64)
    psbt.num_inputs = 1
    psbt.num_outputs = 1
    monkeypatch.setattr(psbt_module.psbtObject, 'input_iter', lambda self: iter([(0, None)]))
    monkeypatch.setattr(psbt_module.psbtInputProxy, 'validate', lambda *args: None)
    asyncio.run(psbt.validate())
    inp.determine_my_signing_key(0, txo, psbt.my_xfp, psbt)
    assert psbt.active_policy.policy_id == policy.policy_id
    assert inp.policy_spend_plan is not None
    assert psbt.active_multisig is None
    assert not psbt.multisig_import_needs_approval


@pytest.mark.parametrize('discovery', ['stored', 'import', 'no_global_xpubs'])
def test_legacy_multisig_discovery_still_validates_and_requests_approval(
        monkeypatch, psbt_module, multi_policy_input, discovery):
    _, make_input = multi_policy_input
    psbt, inp, txo = make_input(registered=False, include_global_xpubs=discovery != 'no_global_xpubs')
    calls = []

    def assert_matching(m, n, paths):
        assert (m, n) == (2, 2)
        assert paths == sorted(inp.subpaths.values())
        calls.append('match')

    def validate_script(witness, subpaths):
        assert witness == inp.get(inp.witness_script)
        assert subpaths == inp.subpaths
        calls.append('script')

    legacy = types.SimpleNamespace(
        M=2, N=2, assert_matching=assert_matching, validate_script=validate_script,
        validate_psbt_xpubs=lambda value: calls.append('xpubs'))

    def import_wallet(m, n, xpubs):
        assert (m, n) == (2, 2)
        assert xpubs == psbt.xpubs
        calls.append('import')
        return legacy, True

    namespace = psbt_module.psbtObject.handle_xpubs.__globals__
    monkeypatch.setitem(namespace, 'disassemble_multisig_mn', lambda _: (2, 2))
    monkeypatch.setitem(namespace, 'MultisigWallet', types.SimpleNamespace(
        find_candidates=lambda paths: [legacy] if discovery == 'stored' else [],
        import_from_psbt=import_wallet, find_match=lambda *args: legacy))
    inp.determine_my_signing_key(0, txo, psbt.my_xfp, psbt)
    assert psbt.active_multisig is legacy
    assert psbt.active_policy is None
    assert inp.policy_spend_plan is None
    assert inp.required_key
    assert psbt.multisig_import_needs_approval == (discovery == 'import')
    assert calls == ({'stored': ['xpubs', 'match', 'script'],
                      'import': ['import', 'match', 'script'],
                      'no_global_xpubs': ['match', 'script']}[discovery])


@pytest.mark.parametrize('policy_first', [False, True])
def test_actual_mixed_policy_and_legacy_inputs_still_fail(
        monkeypatch, psbt_module, multi_policy_input, policy_first):
    policy, make_input = multi_policy_input
    psbt, inp, txo = make_input(registered=not policy_first)
    if policy_first:
        psbt.active_policy = policy
    else:
        psbt.active_multisig = object()
    namespace = psbt_module.psbtObject.handle_xpubs.__globals__
    monkeypatch.setitem(namespace, 'disassemble_multisig_mn', lambda _: (2, 2))
    with pytest.raises(sys.modules['exceptions'].FatalPSBTIssue, match='Cannot mix'):
        inp.determine_my_signing_key(1, txo, psbt.my_xfp, psbt)


@pytest.mark.parametrize('collision', [False, True])
def test_legacy_multisig_ignores_a_nonowned_fingerprint_collision(monkeypatch, psbt_module, collision):
    owned = ec.PrivateKey(bytes([1]) * 32)
    foreign = ec.PrivateKey(bytes([2]) * 32)
    owned_pub = owned.get_public_key().sec()
    foreign_pub = foreign.get_public_key().sec()
    xfp = 0x12345678

    class Node:
        def public_key(self):
            return owned_pub

        def private_key(self):
            return bytearray(owned.secret)

        # The signer derives each input's key from a cached parent node.
        def clone(self):
            return Node()

        def derive(self, index):
            pass

    class Values:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def derive_path(self, *args, **kwargs):
            return Node()

    monkeypatch.setitem(sys.modules, 'stash', types.SimpleNamespace(
        SensitiveValues=Values, blank_object=lambda value: None))
    monkeypatch.setitem(sys.modules, 'errors', types.SimpleNamespace(
        Error=types.SimpleNamespace(PSBT_FATAL_ERROR=1, PSBT_FRAUDULENT_CHANGE_ERROR=2,
                                    OUT_OF_MEMORY_ERROR=3)))
    monkeypatch.setitem(sys.modules, 'foundation', types.SimpleNamespace(
        secp256k1=types.SimpleNamespace(sign_ecdsa=lambda *args: bytes([1]) * 64)))
    monkeypatch.setattr(sys.modules['taproot'], 'taproot_sign_key', lambda *args: None,
                        raising=False)
    inp = types.SimpleNamespace(
        has_utxo=lambda: True,
        required_key={owned_pub, foreign_pub} if collision else {owned_pub}, fully_signed=False,
        scriptSig=b'script', policy_spend_plan=None, is_segwit=True, is_multisig=True,
        tap_subpaths={}, amount=10000, scriptCode=b'script', sighash=1,
        subpaths={owned_pub: [xfp, 0], foreign_pub: [xfp, 0]}, added_sigs=None,
        added_sig=None, tap_key_sig=None,
        get_utxo=lambda n: types.SimpleNamespace(nValue=10000),
        signing_scripts=lambda utxo, idx: (b'script', b'script'))
    # The integrated signer delegates legacy candidate selection to this helper.
    inp.get_signing_node = types.MethodType(psbt_module.psbtInputProxy.get_signing_node, inp)
    psbt = types.SimpleNamespace(
        inputs=[inp], my_xfp=xfp, num_inputs=1, check_unchanged=lambda: None,
        reserve_signatures=lambda: asyncio.sleep(0),
        input_iter=lambda: iter([(0, types.SimpleNamespace(prevout=types.SimpleNamespace(n=0)))]),
        make_txn_segwit_sighash=lambda *args: bytes(32))
    results = []

    async def done(message, code):
        results.append((message, code))

    task = runpy.run_path(str(MODULES / 'tasks/sign_psbt_task.py'))['sign_psbt_task']
    asyncio.run(task(done, psbt))
    assert results == [(None, None)], results
    signatures = dict(inp.added_sigs or {})
    if inp.added_sig:
        signatures[inp.added_sig[0]] = inp.added_sig[1]
    assert set(signatures) == {owned_pub}


def _liana_fixture_constants():
    tree = ast.parse((MODULES / 'tests/unit/wallet_policy_psbt.py').read_text())
    return {node.targets[0].id: ast.literal_eval(node.value)
            for node in tree.body if isinstance(node, ast.Assign) and
            isinstance(node.targets[0], ast.Name) and
            node.targets[0].id in ('LIANA_DESCRIPTOR', 'LIANA_PSBT_BASE64')}


def test_liana_simulator_descriptor_fixture_is_loadable():
    from wallet_policy import MiniscriptPolicy
    descriptor = _liana_fixture_constants()['LIANA_DESCRIPTOR']
    policy = MiniscriptPolicy.from_multipath_descriptor('Liana', 'TBTC', descriptor, (0,))
    assert policy.context == 'wsh'


def test_liana_simulator_psbt_fixture_is_strict_base64():
    encoded = _liana_fixture_constants()['LIANA_PSBT_BASE64']
    assert base64.b64decode(encoded, validate=True).startswith(b'psbt\xff')


def test_flash_signature_store_waits_for_its_last_write(psbt_module, monkeypatch):
    # The next input is read from the same flash chip, so add() must not return while
    # the chip is still programming the signature it just wrote.
    class Chip:
        busy = False

        def wait_done(self):
            self.busy = False

    chip = Chip()

    class File:
        def __init__(self, start, max_size=0):
            self.sf = chip
            self.data = bytearray()

        def tell(self):
            return len(self.data)

        def write(self, data):
            # Like SFFile.write(): returns with the last page program still running.
            self.data += data
            chip.busy = True

    monkeypatch.setitem(sys.modules, 'sffile', types.SimpleNamespace(SFFile=File, SizerFile=object))
    store = psbt_module._FlashSigStore(2)
    assert store.add(1, [(b'\x02' * 33, b'\x30' * 71)]) == 0
    assert not chip.busy
    assert store.add(1, [(b'\x03' * 33, b'\x30' * 70)]) > 0
    assert not chip.busy


@pytest.mark.parametrize('fail_in', ['public_key', 'derive'])
def test_signing_node_is_wiped_when_deriving_it_fails(psbt_module, monkeypatch, fail_in):
    # Until get_signing_node() returns it, nothing else holds the leaf to wipe it.
    wiped = []
    monkeypatch.setitem(sys.modules, 'stash', types.SimpleNamespace(blank_object=wiped.append))

    class Node:
        def __init__(self, leaf=False):
            self.leaf = leaf

        def clone(self):
            return Node(leaf=True)

        def derive(self, index):
            if self.leaf and fail_in == 'derive':
                raise MemoryError

        def public_key(self):
            if self.leaf and fail_in == 'public_key':
                raise MemoryError
            return b'\x02' + b'\x11' * 32

    class Values:
        def derive_path(self, path, register=True):
            return Node()

    xfp = 0x12345678
    inp = types.SimpleNamespace(is_multisig=False, required_key=b'key', tap_subpaths={},
                                subpaths={b'key': [xfp, 84 | 0x80000000, 0, 5]})
    get_signing_node = types.MethodType(psbt_module.psbtInputProxy.get_signing_node, inp)
    with pytest.raises(MemoryError):
        get_signing_node(Values(), xfp, 0, {})
    assert len(wiped) == 1 and wiped[0].leaf


def test_parent_node_cache_is_bounded(psbt_module):
    # A PSBT spread over many accounts derives the rest uncached, and registers no
    # more parents with the session than the cache holds.
    registered = []

    class Node:
        def clone(self):
            return Node()

        def derive(self, index):
            pass

        def public_key(self):
            return b'\x02' + b'\x11' * 32

    class Values:
        def derive_path(self, path, register=True):
            if register:
                registered.append(path)
            return Node()

    parents = {}
    hardened = 0x80000000
    for account in range(20):
        psbt_module.derive_from_parent(Values(), [1, 84 | hardened, hardened, account | hardened, 0, 7],
                                       parents)
    assert len(parents) == 8
    assert len(registered) == 8


def _keypath_to_str(bin_path):
    # utils.keypath_to_str(), which the fixture stubs out.
    rv = 'm/' + '/'.join(str(i & 0x7fffffff) + ("'" if i & 0x80000000 else '') for i in bin_path[1:])
    return 'm' if rv == 'm/' else rv


def test_uncached_leaf_is_wiped_when_its_derivation_fails(psbt_module, monkeypatch):
    # Once the parent cache is full, derive_from_parent() derives the whole path with
    # the real SensitiveValues.derive_path(), which hands its clone to the caller
    # unregistered. Until it does, a failure must wipe the clone.
    wiped = []

    class Node:
        def __init__(self, fail_at=None, path=()):
            self.fail_at = fail_at
            self.path = list(path)

        def clone(self):
            return Node(self.fail_at, self.path)

        def derive(self, index):
            if len(self.path) == self.fail_at:
                raise MemoryError
            self.path.append(index)

        def blank(self):
            wiped.append(self)

        def public_key(self):
            return b'\x02' + b'\x11' * 32

    # The real stash module, with its node type standing in for HDNode.
    monkeypatch.setitem(sys.modules, 'trezorcrypto',
                        types.SimpleNamespace(bip32=types.SimpleNamespace(HDNode=Node)))
    monkeypatch.setitem(sys.modules, 'uctypes', types.ModuleType('uctypes'))
    monkeypatch.setitem(sys.modules, 'pincodes', types.SimpleNamespace(SE_SECRET_LEN=72))
    stash = runpy.run_path(str(MODULES / 'stash.py'))

    class Session:
        derive_path = stash['SensitiveValues'].derive_path
        register = stash['SensitiveValues'].register

        def __init__(self, node):
            self.node = node
            self.spots = []

    monkeypatch.setitem(psbt_module.derive_from_parent.__globals__, 'keypath_to_str', _keypath_to_str)
    hardened = 0x80000000
    path = [1, 84 | hardened, hardened, 9 | hardened, 0, 7]
    parents = {('cached', idx): Node() for idx in range(8)}

    session = Session(Node(fail_at=3))
    with pytest.raises(MemoryError):
        psbt_module.derive_from_parent(session, path, parents)
    assert len(wiped) == 1 and wiped[0].path == path[1:4]
    assert session.spots == [] and len(parents) == 8

    # Without a failure, the uncached leaf reaches the caller, which wipes it.
    wiped.clear()
    session = Session(Node())
    leaf = psbt_module.derive_from_parent(session, path, parents)
    assert leaf.path == path[1:] and wiped == [] and session.spots == []


def test_finalized_save_progress_climbs_through_every_pass(psbt_module, monkeypatch):
    # The real progress module, with a clock that moves 150 ms per reading so every
    # refresh draws. The page must see the percentage climb through the inputs, the
    # witnesses and the transaction ID read back, and never reach 100 before the end.
    clock = types.SimpleNamespace(now=0)

    def ticks_ms():
        clock.now += 150
        return clock.now

    monkeypatch.setitem(sys.modules, 'utime',
                        types.SimpleNamespace(ticks_ms=ticks_ms, ticks_diff=lambda end, begin: end - begin))
    lvgl_task = types.SimpleNamespace(draw=lambda: None)
    monkeypatch.setitem(sys.modules, 'tasks', types.SimpleNamespace(lvgl_task=lvgl_task))
    monkeypatch.setitem(sys.modules, 'tasks.lvgl_task', lvgl_task)
    monkeypatch.setattr(sys.modules['constants'], 'PSBT_MAX_INPUTS', 1000, raising=False)

    psbt_class = psbt_module.psbtObject
    module_globals = psbt_class.finalize.__globals__
    progress = module_globals['progress']
    monkeypatch.setitem(module_globals, 'mem', types.SimpleNamespace(psbt_tmp256=bytearray(256)))
    monkeypatch.setattr(module_globals['history'], 'add_segwit_utxos_finalize', lambda txid: None,
                        raising=False)

    ser = sys.modules['serializations']
    inputs = 100
    raw = struct.pack('<i', 2) + ser.ser_compact_size(inputs)
    for idx in range(inputs):
        raw += ser.CTxIn(ser.COutPoint(idx + 1, 0)).serialize()
    raw += ser.ser_compact_size(1) + ser.CTxOut(1000, b'\x00\x14' + b'\x11' * 20).serialize()
    raw += struct.pack('<I', 0)

    class PSBT:
        input_iter = psbt_class.input_iter
        output_iter = psbt_class.output_iter
        input_witness_iter = psbt_class.input_witness_iter

        def __init__(self):
            self.fd = io.BytesIO(raw)
            self.txn = (0, len(raw))
            self.total_value_out = None

    psbt = PSBT()
    psbt_class.parse_txn(psbt)
    signed = types.SimpleNamespace(is_segwit=True, is_p2sh=False, is_multisig=False, tap_key_sig=None,
                                   added_sig=(b'\x02' + b'\x22' * 32, b'\x30' * 71))
    psbt.inputs = [signed] * inputs
    psbt.outputs = [types.SimpleNamespace(is_change=False, witness_script=None)]

    shown = []
    progress.begin(types.SimpleNamespace(set_progress=shown.append))
    clock.now += 5000   # past the spinner's first seconds
    try:
        psbt_class.finalize(psbt, io.BytesIO())
    finally:
        progress.end()

    assert shown == sorted(shown) and max(shown) <= 99, shown
    assert any(0 < value < 45 for value in shown), shown
    assert any(45 < value < 90 for value in shown), shown
    # The transaction ID is read back in 17 blocks; the page sees it move, up to 99.
    assert len({value for value in shown if value > 90}) >= 5 and max(shown) == 99, shown


def test_signed_psbt_check_steps_through_its_flash_read(psbt_module, monkeypatch):
    # After signing, the whole PSBT is read from flash again and hashed. The page must
    # see that read move the percentage, rather than wait at the start of its share.
    clock = types.SimpleNamespace(now=0)

    def ticks_ms():
        clock.now += 150
        return clock.now

    monkeypatch.setitem(sys.modules, 'utime',
                        types.SimpleNamespace(ticks_ms=ticks_ms, ticks_diff=lambda end, begin: end - begin))
    lvgl_task = types.SimpleNamespace(draw=lambda: None)
    monkeypatch.setitem(sys.modules, 'tasks', types.SimpleNamespace(lvgl_task=lvgl_task))
    monkeypatch.setitem(sys.modules, 'tasks.lvgl_task', lvgl_task)
    psbt_class = psbt_module.psbtObject
    module_globals = psbt_class.finalize.__globals__
    progress = module_globals['progress']
    monkeypatch.setitem(module_globals, 'mem', types.SimpleNamespace(psbt_tmp256=bytearray(256)))

    psbt = types.SimpleNamespace(fd=io.BytesIO(b'Z' * 20 * 256))
    psbt.validated_digest = module_globals['flash_digest'](psbt.fd)

    shown = []
    progress.begin(types.SimpleNamespace(set_progress=shown.append))
    clock.now += 5000
    try:
        progress.phase(94, 97)
        psbt_class.check_unchanged(psbt)
    finally:
        progress.end()
    assert shown == sorted(shown) and {95, 96} <= set(shown) and max(shown) == 97, shown


def test_progress_parts_share_a_phase_between_passes(psbt_module, monkeypatch):
    # A phase made of several passes over the inputs moves through all of them: the
    # later passes don't sit at the point where the first one stopped.
    clock = types.SimpleNamespace(now=0)

    def ticks_ms():
        clock.now += 150
        return clock.now

    monkeypatch.setitem(sys.modules, 'utime',
                        types.SimpleNamespace(ticks_ms=ticks_ms, ticks_diff=lambda end, begin: end - begin))
    lvgl_task = types.SimpleNamespace(draw=lambda: None)
    monkeypatch.setitem(sys.modules, 'tasks', types.SimpleNamespace(lvgl_task=lvgl_task))
    monkeypatch.setitem(sys.modules, 'tasks.lvgl_task', lvgl_task)
    progress = psbt_module.psbtObject.finalize.__globals__['progress']

    shown = []
    progress.begin(types.SimpleNamespace(set_progress=shown.append))
    clock.now += 5000
    try:
        progress.phase(24, 84)
        for lo, hi in ((0, 70), (70, 76), (76, 88), (88, 100)):
            progress.part(lo, hi)
            progress.count(10)
            for _ in range(10):
                progress.step()
            assert shown[-1] == 24 + 60 * hi // 100, (lo, hi, shown)
    finally:
        progress.end()
    assert shown == sorted(shown) and shown[-1] == 84


def test_timelock_and_change_checks_step_once_per_input(psbt_module, monkeypatch):
    # These passes read every input; each input read is a progress step, so the
    # percentage moves through them instead of waiting at the start of their share.
    module_globals = psbt_module.psbtObject.finalize.__globals__
    steps = []
    fake_progress = types.SimpleNamespace(step=lambda: steps.append(1), refresh=lambda: None,
                                          count=lambda total: None, part=lambda lo, hi: None)
    monkeypatch.setitem(module_globals, 'progress', fake_progress)

    inputs = 12
    psbt = types.SimpleNamespace(
        num_inputs=inputs, txn_version=2, lock_time=0, warnings=[],
        inputs=[types.SimpleNamespace(fully_signed=True) for _ in range(inputs)],
        input_iter=lambda: iter([(idx, types.SimpleNamespace(nSequence=0xffffffff))
                                 for idx in range(inputs)]))
    psbt_module.psbtObject.consider_timelocks(psbt)
    assert len(steps) >= inputs
    del steps[:]
    psbt_module.psbtObject.consider_dangerous_change(psbt, 0x12345678)
    assert len(steps) == inputs
