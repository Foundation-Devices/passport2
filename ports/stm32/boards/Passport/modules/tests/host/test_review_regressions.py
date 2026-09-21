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
           keypath_to_str=lambda value: tuple(value), swab32=lambda value: value)
    module('history', verify_amount=lambda *args: None)
    module('sffile', SizerFile=object)
    module('passport', mem=types.SimpleNamespace())
    module('constants', PSBT_MAX_SIZE=1024 * 1024)
    module('multisig_wallet', MultisigWallet=object,
           disassemble_multisig_mn=lambda _: (1, 2))
    module('taproot', output_script=lambda *args: b'', tagged_hash=lambda *args: b'')
    for name in ('public_constants', 'serializations', 'exceptions'):
        loaded = module(name)
        loaded.__dict__.update(runpy.run_path(str(MODULES / (name + '.py'))))
    return types.SimpleNamespace(**runpy.run_path(str(MODULES / 'psbt.py')))


@pytest.mark.parametrize('output_kind', ['p2pkh', 'p2wpkh'])
def test_policy_funds_sent_to_singlesig_are_not_hidden_as_change(monkeypatch, psbt_module, output_kind):
    from wallet_policy import MiniscriptPolicy
    policy = MiniscriptPolicy('Two signers', 'BTC',
                              'wsh(multi(2,@0/**,@1/**))', test_keys(2), (0,))
    root = bip32.HDKey.from_seed(bytes([1]) * 32)
    child = root.derive('m/48h/0h/0h/2h/1/7')
    pubkey = child.get_public_key()
    xfp = int.from_bytes(root.my_fingerprint, 'little')
    path = [xfp, 0x80000030, 0x80000000, 0x80000000, 0x80000002, 1, 7]
    output_script = getattr(script, output_kind)(pubkey).data
    txo = sys.modules['serializations'].CTxOut(10000, output_script)
    output = psbt_module.psbtOutputProxy(io.BytesIO(b'\x00'), 0)
    # Exercise the production derivation decoder using its file-offset values.
    output.fd = io.BytesIO(struct.pack('<7I', *path))
    output.subpaths = {pubkey.sec(): (0, 28)}
    output.validate(0, txo, xfp, None, policy)
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
    assert not output.is_change, 'An output outside the registered policy must be displayed'


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


@pytest.mark.parametrize('include_global_xpubs', [False, True])
def test_registered_multi_policy_is_not_preempted_by_global_xpubs(
        monkeypatch, psbt_module, include_global_xpubs):
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
    if include_global_xpubs:
        legacy = types.SimpleNamespace(validate_psbt_xpubs=lambda value: None)
        psbt_module.psbtObject.handle_xpubs.__globals__['MultisigWallet'] = types.SimpleNamespace(
            find_candidates=lambda paths: [legacy])
        psbt.xpubs = {(struct.pack('<5I', int.from_bytes(bytes.fromhex(key.fingerprint), 'little'),
                                   *key.path), bytes([index])): None
                      for index, key in enumerate(policy.keys)}
        asyncio.run(psbt.handle_xpubs())
    txo = sys.modules['serializations'].CTxOut(10000, derived.script_pubkey)
    inp.determine_my_signing_key(0, txo, xfp, psbt)
    assert psbt.active_policy.policy_id == policy.policy_id
    assert inp.policy_spend_plan is not None


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
        added_sig=None, tap_key_sig=None)
    # The integrated signer delegates legacy candidate selection to this helper.
    inp.get_signing_node = types.MethodType(psbt_module.psbtInputProxy.get_signing_node, inp)
    psbt = types.SimpleNamespace(
        inputs=[inp], my_xfp=xfp,
        input_iter=lambda: iter([(0, types.SimpleNamespace())]),
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
