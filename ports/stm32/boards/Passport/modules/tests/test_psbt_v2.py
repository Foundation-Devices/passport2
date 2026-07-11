# SPDX-FileCopyrightText: 2026 The Passport contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import asyncio
import base64
import binascii
import builtins
import collections
import hashlib
import importlib.util
import io
import struct
import sys
import types
from pathlib import Path

import pytest


MODULES = Path(__file__).parents[1]


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _install_firmware_shims(monkeypatch):
    monkeypatch.setattr(builtins, "const", int, raising=False)
    monkeypatch.setitem(sys.modules, "uio", io)
    monkeypatch.setitem(sys.modules, "ustruct", struct)
    monkeypatch.setitem(sys.modules, "ubinascii", binascii)
    monkeypatch.setitem(sys.modules, "ucollections", collections)

    constants = types.ModuleType("constants")
    constants.PSBT_MAX_SIZE = 1792000
    monkeypatch.setitem(sys.modules, "constants", constants)
    public_constants = _load_module(
        "public_constants", MODULES / "public_constants.py")

    trezorcrypto = types.ModuleType("trezorcrypto")
    trezorcrypto.sha256 = hashlib.sha256
    monkeypatch.setitem(sys.modules, "trezorcrypto", trezorcrypto)

    _load_module("opcodes", MODULES / "opcodes.py")

    utils = types.ModuleType("utils")
    utils.xfp2str = lambda value: "%08x" % value
    utils.B2A = lambda value: binascii.hexlify(value).decode()
    utils.bytes_to_hex_str = lambda value: binascii.hexlify(value).decode()
    utils.keypath_to_str = lambda path, skip=0: "/".join(
        str(value) for value in path[skip:])
    utils.swab32 = lambda value: int.from_bytes(
        value.to_bytes(4, "little"), "big")
    monkeypatch.setitem(sys.modules, "utils", utils)

    serializations = _load_module(
        "serializations", MODULES / "serializations.py")

    history = types.ModuleType("history")
    history.verify_amount = lambda *args: None
    history.add_segwit_utxos = lambda *args: None
    history.add_segwit_utxos_finalize = lambda *args: None
    monkeypatch.setitem(sys.modules, "history", history)

    sffile = types.ModuleType("sffile")
    sffile.SizerFile = io.BytesIO
    monkeypatch.setitem(sys.modules, "sffile", sffile)

    passport = types.ModuleType("passport")
    passport.mem = types.SimpleNamespace(psbt_tmp256=bytearray(256))
    monkeypatch.setitem(sys.modules, "passport", passport)

    multisig = types.ModuleType("multisig_wallet")
    multisig.MultisigWallet = type("MultisigWallet", (), {})
    multisig.disassemble_multisig_mn = lambda script: (1, 1)
    monkeypatch.setitem(sys.modules, "multisig_wallet", multisig)

    exceptions = _load_module("exceptions", MODULES / "exceptions.py")

    taproot = types.ModuleType("taproot")
    taproot.output_script = lambda key, root: b"\x51\x20" + key
    taproot.tagged_hash = lambda tag, message: hashlib.sha256(message).digest()
    monkeypatch.setitem(sys.modules, "taproot", taproot)

    common = types.ModuleType("common")
    common.settings = types.SimpleNamespace(get=lambda key, default=0: default)
    monkeypatch.setitem(sys.modules, "common", common)

    psbt = _load_module("psbt_v2_under_test", MODULES / "psbt.py")
    return psbt, public_constants, serializations, exceptions


@pytest.fixture
def firmware(monkeypatch):
    return _install_firmware_shims(monkeypatch)


def _compact(value):
    assert 0 <= value < 253
    return bytes([value])


def _entry(key_type, value, key_data=b""):
    key = bytes([key_type]) + key_data
    return _compact(len(key)) + key + _compact(len(value)) + value


def _map(entries):
    return b"".join(entries) + b"\x00"


def _psbt_v2(public_constants, inputs, outputs, fallback_locktime=0,
             modifiable=None):
    globals_entries = [
        _entry(public_constants.PSBT_GLOBAL_TX_VERSION,
               struct.pack("<i", 2)),
        _entry(public_constants.PSBT_GLOBAL_FALLBACK_LOCKTIME,
               struct.pack("<I", fallback_locktime)),
        _entry(public_constants.PSBT_GLOBAL_INPUT_COUNT,
               _compact(len(inputs))),
        _entry(public_constants.PSBT_GLOBAL_OUTPUT_COUNT,
               _compact(len(outputs))),
        _entry(public_constants.PSBT_GLOBAL_VERSION,
               struct.pack("<I", 2)),
    ]
    if modifiable is not None:
        globals_entries.insert(-1, _entry(
            public_constants.PSBT_GLOBAL_TX_MODIFIABLE, bytes([modifiable])))
    globals_map = _map(globals_entries)
    return b"psbt\xff" + globals_map + b"".join(inputs) + b"".join(outputs)


def _input_map(public_constants, marker, height=None, timestamp=None,
               sighash=None):
    entries = [
        _entry(public_constants.PSBT_IN_PREVIOUS_TXID, bytes([marker]) * 32),
        _entry(public_constants.PSBT_IN_OUTPUT_INDEX, struct.pack("<I", marker)),
        _entry(public_constants.PSBT_IN_SEQUENCE, struct.pack("<I", 0xfffffffd)),
    ]
    if height is not None:
        entries.append(_entry(
            public_constants.PSBT_IN_REQUIRED_HEIGHT_LOCKTIME,
            struct.pack("<I", height)))
    if timestamp is not None:
        entries.append(_entry(
            public_constants.PSBT_IN_REQUIRED_TIME_LOCKTIME,
            struct.pack("<I", timestamp)))
    if sighash is not None:
        entries.append(_entry(
            public_constants.PSBT_IN_SIGHASH_TYPE,
            struct.pack("<I", sighash)))
    return _map(entries)


def _output_map(public_constants, amount, script=None, sp_info=None):
    entries = [_entry(
        public_constants.PSBT_OUT_AMOUNT, struct.pack("<q", amount))]
    if script is not None:
        entries.append(_entry(public_constants.PSBT_OUT_SCRIPT, script))
    if sp_info is not None:
        entries.append(_entry(public_constants.PSBT_OUT_SP_V0_INFO, sp_info))
    return _map(entries)


def _psbt_v0(public_constants, amount, script):
    txin = b"\x01" * 32 + struct.pack("<I", 0) + b"\x00" + struct.pack(
        "<I", 0xfffffffd)
    txout = struct.pack("<q", amount) + _compact(len(script)) + script
    unsigned_tx = (struct.pack("<i", 2) + b"\x01" + txin + b"\x01" +
                   txout + struct.pack("<I", 0))
    return (b"psbt\xff" + _map([_entry(
        public_constants.PSBT_GLOBAL_UNSIGNED_TX, unsigned_tx)]) +
        _map([]) + _map([]))


def test_reads_reconstructs_and_round_trips_psbt_v2(firmware):
    psbt, constants, _, _ = firmware
    script = b"\x00\x14" + b"\x22" * 20
    payload = _psbt_v2(
        constants,
        [_input_map(constants, 1)],
        [_output_map(constants, 2500, script)],
        fallback_locktime=42)

    parsed = psbt.psbtObject.read_psbt(io.BytesIO(payload))

    assert parsed.psbt_version == 2
    assert parsed.txn_version == 2
    assert parsed.lock_time == 42
    input_index, txin = next(parsed.input_iter())
    assert input_index == 0
    assert txin.prevout.serialize() == b"\x01" * 32 + struct.pack("<I", 1)
    assert txin.nSequence == 0xfffffffd
    output_index, txout = next(parsed.output_iter())
    assert output_index == 0
    assert txout.nValue == 2500
    assert txout.scriptPubKey == script

    encoded = io.BytesIO()
    parsed.serialize(encoded)
    reparsed = psbt.psbtObject.read_psbt(io.BytesIO(encoded.getvalue()))
    assert reparsed.psbt_version == 2
    assert next(reparsed.input_iter())[1].prevout.serialize() == txin.prevout.serialize()
    assert next(reparsed.output_iter())[1].serialize() == txout.serialize()


def test_preserves_existing_psbt_v0_path(firmware):
    psbt, constants, _, _ = firmware
    script = b"\x00\x14" + b"\x21" * 20
    payload = _psbt_v0(constants, 3000, script)

    parsed = psbt.psbtObject.read_psbt(io.BytesIO(payload))

    assert parsed.psbt_version == 0
    assert parsed.lock_time == 0
    assert next(parsed.input_iter())[1].prevout.serialize() == (
        b"\x01" * 32 + struct.pack("<I", 0))
    assert next(parsed.output_iter())[1].scriptPubKey == script
    encoded = io.BytesIO()
    parsed.serialize(encoded)
    reparsed = psbt.psbtObject.read_psbt(io.BytesIO(encoded.getvalue()))
    assert reparsed.psbt_version == 0
    assert next(reparsed.output_iter())[1].nValue == 3000


def test_selects_height_locktime_when_all_constrained_inputs_support_it(firmware):
    psbt, constants, _, _ = firmware
    script = b"\x00\x14" + b"\x33" * 20
    payload = _psbt_v2(
        constants,
        [_input_map(constants, 1, height=100, timestamp=500000100),
         _input_map(constants, 2, height=120)],
        [_output_map(constants, 5000, script)])

    parsed = psbt.psbtObject.read_psbt(io.BytesIO(payload))

    assert parsed.lock_time == 120


def test_accepts_uncomputed_bip375_output_but_refuses_to_render_it(firmware):
    psbt, constants, _, exceptions = firmware
    sp_info = b"\x02" + b"\x44" * 32 + b"\x03" + b"\x55" * 32
    payload = _psbt_v2(
        constants,
        [_input_map(constants, 1)],
        [_output_map(constants, 1000, sp_info=sp_info)])
    parsed = psbt.psbtObject.read_psbt(io.BytesIO(payload))

    assert parsed.outputs[0].get_sp_v0_info() == sp_info
    with pytest.raises(exceptions.FatalPSBTIssue, match="has not been computed"):
        next(parsed.output_iter())

    computed = b"\x51\x20" + b"\x66" * 32
    parsed.outputs[0].computed_script = computed
    assert next(parsed.output_iter())[1].scriptPubKey == computed


def test_rejects_incompatible_psbt_v2_locktimes(firmware):
    psbt, constants, _, exceptions = firmware
    script = b"\x00\x14" + b"\x77" * 20
    payload = _psbt_v2(
        constants,
        [_input_map(constants, 1, height=100),
         _input_map(constants, 2, timestamp=500000100)],
        [_output_map(constants, 5000, script)])

    with pytest.raises(exceptions.FatalPSBTIssue, match="incompatible"):
        psbt.psbtObject.read_psbt(io.BytesIO(payload))


def test_rejects_computed_silent_output_when_transaction_is_modifiable(firmware):
    psbt, constants, _, _ = firmware
    sp_info = b"\x02" + b"\x44" * 32 + b"\x03" + b"\x55" * 32
    script = b"\x51\x20" + b"\x66" * 32
    payload = _psbt_v2(
        constants,
        [_input_map(constants, 1)],
        [_output_map(constants, 1000, script=script, sp_info=sp_info)],
        modifiable=1)

    with pytest.raises(AssertionError, match="remains modifiable"):
        psbt.psbtObject.read_psbt(io.BytesIO(payload))


def test_prepares_and_locks_uncomputed_silent_output(firmware, monkeypatch):
    psbt, constants, _, exceptions = firmware
    sp_info = b"\x02" + b"\x44" * 32 + b"\x03" + b"\x55" * 32
    payload = _psbt_v2(
        constants,
        [_input_map(constants, 1)],
        [_output_map(constants, 1000, sp_info=sp_info)],
        modifiable=3)
    parsed = psbt.psbtObject.read_psbt(io.BytesIO(payload))
    expected_script = b"\x51\x20" + b"\x66" * 32
    share = b"\x02" + b"\x77" * 32
    proof = b"\x88" * 64
    silent_payments = types.ModuleType("silent_payments")
    silent_payments.create_bip375_data_from_psbt = (
        lambda psbt_obj, output_info, sensitive_values:
        ({0: expected_script}, {sp_info[:33]: (share, proof)}))
    monkeypatch.setitem(sys.modules, "silent_payments", silent_payments)

    parsed.prepare_silent_payment_outputs(object())

    assert parsed.outputs[0].computed_script == expected_script
    assert parsed.sp_ecdh_shares == {sp_info[:33]: share}
    assert parsed.sp_dleq_proofs == {sp_info[:33]: proof}
    assert parsed.tx_modifiable == 0
    assert next(parsed.output_iter())[1].scriptPubKey == expected_script

    encoded = io.BytesIO()
    parsed.serialize(encoded)
    reparsed = psbt.psbtObject.read_psbt(io.BytesIO(encoded.getvalue()))
    assert reparsed.tx_modifiable == 0
    assert reparsed.outputs[0].get_sp_v0_info() == sp_info
    assert reparsed.outputs[0].get_output_script() == expected_script
    assert set(reparsed.sp_ecdh_shares) == {sp_info[:33]}
    assert set(reparsed.sp_dleq_proofs) == {sp_info[:33]}

    parsed.outputs[0].computed_script = b"\x51\x20" + b"\x99" * 32
    parsed.outputs[0].output_script = (0, 34)
    with pytest.raises(exceptions.FatalPSBTIssue):
        parsed.prepare_silent_payment_outputs(object())


def test_silent_payment_validation_requires_sighash_all(firmware):
    psbt, constants, _, exceptions = firmware
    sp_info = b"\x02" + b"\x44" * 32 + b"\x03" + b"\x55" * 32
    payload = _psbt_v2(
        constants,
        [_input_map(constants, 1, sighash=0)],
        [_output_map(constants, 1000, sp_info=sp_info)])
    parsed = psbt.psbtObject.read_psbt(io.BytesIO(payload))

    with pytest.raises(exceptions.FatalPSBTIssue, match="SIGHASH_ALL"):
        asyncio.run(parsed.validate())

    payload = _psbt_v2(
        constants,
        [_input_map(constants, 1)],
        [_output_map(constants, 1000, sp_info=sp_info)])
    parsed = psbt.psbtObject.read_psbt(io.BytesIO(payload))
    asyncio.run(parsed.validate())
    assert parsed.inputs[0].sighash == 1

    tap_script_sig = _entry(
        constants.PSBT_IN_TAP_SCRIPT_SIG, b"\x11" * 64,
        key_data=b"\x22" * 64)
    input_map = _input_map(constants, 1)[:-1] + tap_script_sig + b"\x00"
    payload = _psbt_v2(
        constants,
        [input_map],
        [_output_map(constants, 1000, sp_info=sp_info)])
    parsed = psbt.psbtObject.read_psbt(io.BytesIO(payload))
    with pytest.raises(exceptions.FatalPSBTIssue, match="SIGHASH_ALL"):
        asyncio.run(parsed.validate())


def test_prepares_official_bip375_vector(firmware, monkeypatch):
    import test_silent_payments as silent_tests

    psbt, _, _, _ = firmware
    silent_tests._install_crypto_shims(monkeypatch)
    blanked = silent_tests._install_psbt_adapter_shims(monkeypatch)
    _load_module("silent_payments", MODULES / "silent_payments.py")

    # BIP375 v1.1 valid vector 0: one P2PKH input, single signer.
    encoded = (
        "cHNidP8B+wQCAAAAAQIEAgAAAAEEAQEBBQEBAQYBAAABDiBSJ0jrF3ZNKMpJSBXsjUnn0w1SvHNC"
        "LHyG63TjlwVylAEPBAAAAAABAFUCAAAAAfTCEtWu0ef2/2M/LOCcZHxXvt2TAxTZjed1A9WOlAsz"
        "AAAAAAD/////AaCGAQAAAAAAGXapFB4q14ctMpQTpW3wlovjOCIngxY7iKwAAAAAIgICyBe7dSGv"
        "w16pbzv7Jw5utQ3f+lVgYnuWH+wA8pllCL9HMEQCIDnBDcvHz0XG2UNW/1DBK42GqVUM8DcXPZzr"
        "94cU5nx1AiBxlVpC7SBTJDIHI8TwFCXc6J9CX4NwKEy0J2z9tt6jrAEBAwQBAAAAIgYCyBe7dSGv"
        "w16pbzv7Jw5utQ3f+lVgYnuWH+wA8pllCL8IAAAAgAAAAAABEAT+////Ih0Cekh/wZ+3aYd7h0LW"
        "6hgRjzxOcrHqjG3mAqetSkHb4GghA+yk/xG3KOLg9gzmIilDpv9VudlfYnv5qZ0IS8hy1QpbIh4C"
        "ekh/wZ+3aYd7h0LW6hgRjzxOcrHqjG3mAqetSkHb4GhAihOzmFVF9yvW6JcUrrkJs+NUqEKpu4tW"
        "zQ7e0h34oZlZizEiikngvX6VzhBT98WyistUOmhwdgDjzomCLuMgIQABAwgYcwEAAAAAAAEEIlEg"
        "4UDSh7RbRs1OqvpDdwYVcLq+g9G4vJUKdKn+oJIz16YBCUICekh/wZ+3aYd7h0LW6hgRjzxOcrHq"
        "jG3mAqetSkHb4GgDYeGx6d5eQssgB/fKVLng1X7ROTj61W0/GeV1E6j84DkA"
    )
    parsed = psbt.psbtObject.read_psbt(
        io.BytesIO(base64.b64decode(encoded)))
    psbt_input = parsed.inputs[0]
    derivation = psbt_input.get(next(iter(psbt_input.subpaths.values())))
    parsed.my_xfp = struct.unpack("<I", derivation[:4])[0]
    psbt_input.parse_subpaths(parsed.my_xfp)
    public_key, path = next(iter(psbt_input.subpaths.items()))
    psbt_input.required_key = public_key
    private_key = bytes.fromhex(
        "7e31eeeb1aa2597b6d63b357541461d75ddae76b7603d24619f5ebed9e88ec31")
    sensitive_values = silent_tests.FakeSensitiveValues({
        "0": silent_tests.FakeNode(public_key, private_key),
    })

    parsed.prepare_silent_payment_outputs(sensitive_values)

    expected_script = bytes.fromhex(
        "5120e140d287b45b46cd4eaafa4377061570babe83d1b8bc950a74a9fea09233d7a6")
    assert parsed.outputs[0].computed_script == expected_script
    assert parsed.tx_modifiable == 0
    assert len(parsed.sp_ecdh_shares) == 1
    assert len(parsed.sp_dleq_proofs) == 1
    assert private_key in blanked

    serialized = io.BytesIO()
    parsed.serialize(serialized)
    reparsed = psbt.psbtObject.read_psbt(
        io.BytesIO(serialized.getvalue()))
    assert reparsed.outputs[0].get_output_script() == expected_script
