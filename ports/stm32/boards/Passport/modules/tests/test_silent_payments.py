# SPDX-FileCopyrightText: 2026 The Passport contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import hashlib
import importlib.util
import sys
import types
from pathlib import Path

import pytest


FIELD_PRIME = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
GENERATOR = (
    0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
    0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8,
)
SCAN_KEY = bytes.fromhex(
    "0220bcfac5b99e04ad1a06ddfb016ee13582609d60b6291e98d01a9bc9a16c96d4")
SPEND_KEY = bytes.fromhex(
    "025cc9856d6f8375350e123978daac200c260cb5b5ae83106cab90484dcd8fcf36")
SILENT_PAYMENT_ADDRESS = (
    "sp1qqgste7k9hx0qftg6qmwlkqtwuy6cycyavzmzj85c6qdfhjdpdjtdgqjuexzk6"
    "murw56suy3e0rd2cgqvycxttddwsvgxe2usfpxumr70xc9pkqwv")


def _point_add(left, right):
    if left is None:
        return right
    if right is None:
        return left
    if left[0] == right[0] and (left[1] + right[1]) % FIELD_PRIME == 0:
        return None
    if left == right:
        slope = (3 * left[0] * left[0] *
                 pow(2 * left[1], FIELD_PRIME - 2, FIELD_PRIME)) % FIELD_PRIME
    else:
        slope = ((right[1] - left[1]) *
                 pow(right[0] - left[0], FIELD_PRIME - 2, FIELD_PRIME)) % FIELD_PRIME
    x_coord = (slope * slope - left[0] - right[0]) % FIELD_PRIME
    y_coord = (slope * (left[0] - x_coord) - left[1]) % FIELD_PRIME
    return x_coord, y_coord


def _point_multiply(scalar, point):
    result = None
    addend = point
    while scalar:
        if scalar & 1:
            result = _point_add(result, addend)
        addend = _point_add(addend, addend)
        scalar >>= 1
    return result


def _parse_public_key(public_key):
    if public_key[0] == 4:
        return (int.from_bytes(public_key[1:33], "big"),
                int.from_bytes(public_key[33:], "big"))
    x_coord = int.from_bytes(public_key[1:], "big")
    y_coord = pow((pow(x_coord, 3, FIELD_PRIME) + 7) % FIELD_PRIME,
                  (FIELD_PRIME + 1) // 4, FIELD_PRIME)
    if (y_coord & 1) != (public_key[0] & 1):
        y_coord = FIELD_PRIME - y_coord
    return x_coord, y_coord


def _uncompressed(point):
    return b"\x04" + point[0].to_bytes(32, "big") + point[1].to_bytes(32, "big")


def _install_crypto_shims(monkeypatch):
    class FakeSecp256k1:
        @staticmethod
        def multiply(secret_key, public_key):
            return _uncompressed(_point_multiply(
                int.from_bytes(secret_key, "big"), _parse_public_key(public_key)))

    class FakeEcdsa:
        @staticmethod
        def scalar_multiply(secret_key):
            point = _point_multiply(int.from_bytes(secret_key, "big"), GENERATOR)
            return point[0].to_bytes(32, "big"), point[1].to_bytes(32, "big")

        @staticmethod
        def point_add(x1, y1, x2, y2):
            point = _point_add(
                (int.from_bytes(x1, "big"), int.from_bytes(y1, "big")),
                (int.from_bytes(x2, "big"), int.from_bytes(y2, "big")))
            return point[0].to_bytes(32, "big"), point[1].to_bytes(32, "big")

    foundation = types.ModuleType("foundation")
    foundation.secp256k1 = FakeSecp256k1
    trezorcrypto = types.ModuleType("trezorcrypto")
    trezorcrypto.sha256 = hashlib.sha256
    trezorcrypto.ecdsa = FakeEcdsa
    monkeypatch.setitem(sys.modules, "foundation", foundation)
    monkeypatch.setitem(sys.modules, "trezorcrypto", trezorcrypto)


def _install_psbt_adapter_shims(monkeypatch, taproot_key=None):
    blanked = []

    stash = types.ModuleType("stash")
    stash.blank_object = blanked.append
    monkeypatch.setitem(sys.modules, "stash", stash)

    taproot = types.ModuleType("taproot")
    taproot.taproot_tweak_seckey = lambda private_key, tree_hash: taproot_key
    monkeypatch.setitem(sys.modules, "taproot", taproot)

    utils = types.ModuleType("utils")
    utils.keypath_to_str = lambda path: "/".join(str(item) for item in path[1:])
    utils.swab32 = lambda value: int.from_bytes(
        value.to_bytes(4, "little"), "big")
    monkeypatch.setitem(sys.modules, "utils", utils)
    return blanked


class FakeNode:
    def __init__(self, public_key, private_key):
        self._public_key = public_key
        self._private_key = private_key

    def public_key(self):
        return self._public_key

    def private_key(self):
        return self._private_key


class FakeSensitiveValues:
    def __init__(self, nodes):
        self.nodes = nodes

    def derive_path(self, path, register=False):
        assert register is False
        return self.nodes[path]


class FakePrevout:
    def __init__(self, serialized, index):
        self.serialized = serialized
        self.n = index

    def serialize(self):
        return self.serialized


class FakeTxIn:
    def __init__(self, outpoint, index):
        self.prevout = FakePrevout(outpoint, index)


class FakeUtxo:
    def __init__(self, address_type, is_segwit=False):
        self.address_type = address_type
        self.is_segwit = is_segwit

    def get_address(self):
        return self.address_type, b"", self.is_segwit


class FakePsbtInput:
    def __init__(self, utxo, required_key=None, subpaths=None,
                 tap_subpaths=None, redeem_script=None):
        self.utxo_value = utxo
        self.required_key = required_key
        self.subpaths = subpaths or {}
        self.tap_subpaths = tap_subpaths or {}
        self.redeem_script = redeem_script

    def has_utxo(self):
        return True

    def get_utxo(self, index):
        return self.utxo_value

    def get(self, value):
        return value


class FakePsbt:
    def __init__(self, xfp, inputs, outpoints):
        self.my_xfp = xfp
        self.inputs = inputs
        self.txins = [FakeTxIn(outpoint, 0) for outpoint in outpoints]

    def input_iter(self):
        return enumerate(self.txins)


@pytest.fixture
def silent_payments(monkeypatch):
    _install_crypto_shims(monkeypatch)
    module_path = Path(__file__).parents[1] / "silent_payments.py"
    spec = importlib.util.spec_from_file_location("silent_payments", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _outpoint(txid, index):
    return bytes.fromhex(txid)[::-1] + index.to_bytes(4, "little")


def _encode_address(silent_payments, hrp, version, key_data):
    payload = [version] + list(
        silent_payments._convert_bits(key_data, 8, 5, True))
    values = silent_payments._bech32_hrp_expand(hrp) + payload + [0] * 6
    polymod = (silent_payments._bech32_polymod(values) ^
               silent_payments.BECH32M_CONST)
    checksum = [(polymod >> (5 * (5 - index))) & 31 for index in range(6)]
    return hrp + "1" + "".join(
        silent_payments._BECH32_CHARSET[value] for value in payload + checksum)


def _legacy_inputs():
    return [
        (bytes.fromhex("eadc78165ff1f8ea94ad7cfdc54990738a4c53f6e0507b42154201b8e5dff3b1"), False),
        (bytes.fromhex("93f5ed907ad5b2bdbbdcb5d9116ebc0a4e1f92f910d5260237fa45a9408aad16"), False),
    ]


def test_decodes_official_v0_address(silent_payments):
    assert silent_payments.decode_address(SILENT_PAYMENT_ADDRESS) == (
        "sp", 0, SCAN_KEY, SPEND_KEY)
    assert silent_payments.decode_address(
        SILENT_PAYMENT_ADDRESS.upper(), expected_hrp="sp") == (
            "sp", 0, SCAN_KEY, SPEND_KEY)


def test_rejects_mixed_case_wrong_network_and_bad_checksum(silent_payments):
    mixed_case = "S" + SILENT_PAYMENT_ADDRESS[1:]
    with pytest.raises(ValueError, match="mixed-case"):
        silent_payments.decode_address(mixed_case)
    with pytest.raises(ValueError, match="network mismatch"):
        silent_payments.decode_address(SILENT_PAYMENT_ADDRESS, expected_hrp="tsp")
    with pytest.raises(ValueError, match="checksum"):
        silent_payments.decode_address(SILENT_PAYMENT_ADDRESS[:-1] + "p")


def test_enforces_version_length_and_forward_compatibility(silent_payments):
    short_v0 = _encode_address(silent_payments, "sp", 0, SCAN_KEY)
    with pytest.raises(ValueError, match="66 key bytes"):
        silent_payments.decode_address(short_v0)

    extended_v1 = _encode_address(
        silent_payments, "tsp", 1, SCAN_KEY + SPEND_KEY + b"extension")
    assert silent_payments.decode_address(extended_v1) == (
        "tsp", 1, SCAN_KEY, SPEND_KEY)

    reserved_v31 = _encode_address(
        silent_payments, "sp", 31, SCAN_KEY + SPEND_KEY)
    with pytest.raises(ValueError, match="unsupported"):
        silent_payments.decode_address(reserved_v31)


def test_rejects_invalid_public_keys_with_valid_checksum(silent_payments):
    invalid_keys = bytes([4]) + SCAN_KEY[1:] + SPEND_KEY
    address = _encode_address(silent_payments, "sp", 0, invalid_keys)
    with pytest.raises(ValueError, match="compressed or uncompressed"):
        silent_payments.decode_address(address)


def test_derives_output_script_from_owned_psbt_inputs(
        silent_payments, monkeypatch):
    blanked = _install_psbt_adapter_shims(monkeypatch)
    xfp = 0x12345678
    private_keys = [secret for secret, _ in _legacy_inputs()]
    public_keys = [
        bytes.fromhex(
            "025a1e61f898173040e20616d43e9f496fba90338a39faa1ed98fcbaeee4dd9be5"),
        bytes.fromhex(
            "03bd85685d03d111699b15d046319febe77f8de5286e9e512703cdee1bf3be3792"),
    ]
    inputs = [
        FakePsbtInput(
            FakeUtxo("p2pkh"), key, {key: [xfp, index + 1]})
        for index, key in enumerate(public_keys)
    ]
    outpoints = [
        _outpoint(
            "f4184fc596403b9d638783cf57adfe4c75c605f6356fbc91338530e9831e9e16", 0),
        _outpoint(
            "a1075db55d416d3ca199f55b6084e2115b9345e16c5cf302fc80e9d5fbf5d48d", 0),
    ]
    psbt = FakePsbt(xfp, inputs, outpoints)
    sensitive_values = FakeSensitiveValues({
        str(index + 1): FakeNode(public_keys[index], private_keys[index])
        for index in range(2)
    })

    scripts = silent_payments.create_output_scripts_from_psbt(
        psbt, [SILENT_PAYMENT_ADDRESS], sensitive_values, expected_hrp="sp")
    assert scripts == [b"\x51\x20" + bytes.fromhex(
        "3e9fce73d4e77a4809908e3c3a2e54ee147b9312dc5044a193d1fc85de46e3c1")]
    assert private_keys[0] in blanked and private_keys[1] in blanked


def test_rejects_external_eligible_psbt_input(silent_payments, monkeypatch):
    _install_psbt_adapter_shims(monkeypatch)
    psbt = FakePsbt(
        0x12345678,
        [FakePsbtInput(FakeUtxo("p2pkh"))],
        [_outpoint("00" * 32, 0)])
    with pytest.raises(ValueError, match="not controlled"):
        silent_payments.create_output_scripts_from_psbt(
            psbt, [SILENT_PAYMENT_ADDRESS], FakeSensitiveValues({}))


def test_tweaks_taproot_psbt_input_and_blanks_keys(
        silent_payments, monkeypatch):
    output_private_key = bytes.fromhex("11" * 32)
    blanked = _install_psbt_adapter_shims(monkeypatch, output_private_key)
    captured = {}

    def capture_create_outputs(keys, outpoints, recipients):
        captured["keys"] = list(keys)
        return [bytes.fromhex("44" * 32)]

    monkeypatch.setattr(
        silent_payments, "create_outputs", capture_create_outputs)

    xfp = 0x12345678
    internal_key = bytes.fromhex("22" * 32)
    internal_private_key = bytes.fromhex("33" * 32)
    psbt_input = FakePsbtInput(
        FakeUtxo("p2tr", True), internal_key,
        tap_subpaths={internal_key: ([xfp, 1], [])})
    psbt = FakePsbt(xfp, [psbt_input], [_outpoint("01" * 32, 0)])
    sensitive_values = FakeSensitiveValues({
        "1": FakeNode(b"\x02" + internal_key, internal_private_key)
    })

    scripts = silent_payments.create_output_scripts_from_psbt(
        psbt, [SILENT_PAYMENT_ADDRESS], sensitive_values)
    assert scripts == [b"\x51\x20" + bytes.fromhex("44" * 32)]
    assert captured["keys"] == [(output_private_key, True)]
    assert internal_private_key in blanked
    assert output_private_key in blanked


def test_skips_p2pk_and_accepts_wrapped_p2wpkh(
        silent_payments, monkeypatch):
    blanked = _install_psbt_adapter_shims(monkeypatch)
    captured = {}

    def capture_create_outputs(keys, outpoints, recipients):
        captured["keys"] = list(keys)
        captured["outpoints"] = list(outpoints)
        return [bytes.fromhex("55" * 32)]

    monkeypatch.setattr(
        silent_payments, "create_outputs", capture_create_outputs)

    xfp = 0x12345678
    public_key = bytes.fromhex(
        "025a1e61f898173040e20616d43e9f496fba90338a39faa1ed98fcbaeee4dd9be5")
    private_key = _legacy_inputs()[0][0]
    outpoints = [_outpoint("02" * 32, 0), _outpoint("03" * 32, 1)]
    inputs = [
        FakePsbtInput(FakeUtxo("p2pk")),
        FakePsbtInput(
            FakeUtxo("p2sh"), public_key, {public_key: [xfp, 1]},
            redeem_script=b"\x00\x14" + bytes(20)),
    ]
    psbt = FakePsbt(xfp, inputs, outpoints)
    sensitive_values = FakeSensitiveValues({
        "1": FakeNode(public_key, private_key)
    })

    scripts = silent_payments.create_output_scripts_from_psbt(
        psbt, [SILENT_PAYMENT_ADDRESS], sensitive_values)
    assert scripts == [b"\x51\x20" + bytes.fromhex("55" * 32)]
    assert captured["keys"] == [(private_key, False)]
    assert captured["outpoints"] == outpoints
    assert private_key in blanked


def test_blanks_private_keys_when_output_derivation_fails(
        silent_payments, monkeypatch):
    blanked = _install_psbt_adapter_shims(monkeypatch)

    def fail_create_outputs(keys, outpoints, recipients):
        raise RuntimeError("derivation failed")

    monkeypatch.setattr(
        silent_payments, "create_outputs", fail_create_outputs)
    xfp = 0x12345678
    public_key = bytes.fromhex(
        "025a1e61f898173040e20616d43e9f496fba90338a39faa1ed98fcbaeee4dd9be5")
    private_key = _legacy_inputs()[0][0]
    psbt = FakePsbt(
        xfp,
        [FakePsbtInput(
            FakeUtxo("p2pkh"), public_key, {public_key: [xfp, 1]})],
        [_outpoint("04" * 32, 0)])
    sensitive_values = FakeSensitiveValues({
        "1": FakeNode(public_key, private_key)
    })

    with pytest.raises(RuntimeError, match="derivation failed"):
        silent_payments.create_output_scripts_from_psbt(
            psbt, [SILENT_PAYMENT_ADDRESS], sensitive_values)
    assert private_key in blanked


def test_official_simple_send_vector(silent_payments):
    outpoints = [
        _outpoint("f4184fc596403b9d638783cf57adfe4c75c605f6356fbc91338530e9831e9e16", 0),
        _outpoint("a1075db55d416d3ca199f55b6084e2115b9345e16c5cf302fc80e9d5fbf5d48d", 0),
    ]
    outputs, secrets = silent_payments.create_outputs_with_shared_secrets(
        _legacy_inputs(), outpoints, [(SCAN_KEY, SPEND_KEY)])
    assert outputs == [bytes.fromhex(
        "3e9fce73d4e77a4809908e3c3a2e54ee147b9312dc5044a193d1fc85de46e3c1")]
    assert secrets == [bytes.fromhex(
        "028158aff7d61ea66b2fa7f555bc3c5937d1debbde16423d630f9aa7943e14d80d")]


def test_official_outpoint_selection_vector(silent_payments):
    txid = "f4184fc596403b9d638783cf57adfe4c75c605f6356fbc91338530e9831e9e16"
    outputs = silent_payments.create_outputs(
        _legacy_inputs(),
        [_outpoint(txid, 3), _outpoint(txid, 7)],
        [(SCAN_KEY, SPEND_KEY)])
    assert outputs == [bytes.fromhex(
        "79e71baa2ba3fc66396de3a04f168c7bf24d6870ec88ca877754790c1db357b6")]


def test_official_mixed_taproot_parity_vector(silent_payments):
    inputs = [
        (bytes.fromhex("eadc78165ff1f8ea94ad7cfdc54990738a4c53f6e0507b42154201b8e5dff3b1"), True),
        (bytes.fromhex("1d37787c2b7116ee983e9f9c13269df29091b391c04db94239e0d2bc2182c3bf"), True),
    ]
    outpoints = [
        _outpoint("f4184fc596403b9d638783cf57adfe4c75c605f6356fbc91338530e9831e9e16", 0),
        _outpoint("a1075db55d416d3ca199f55b6084e2115b9345e16c5cf302fc80e9d5fbf5d48d", 0),
    ]
    outputs = silent_payments.create_outputs(
        inputs, outpoints, [(SCAN_KEY, SPEND_KEY)])
    assert outputs == [bytes.fromhex(
        "77cab7dd12b10259ee82c6ea4b509774e33e7078e7138f568092241bf26b99f1")]


def test_official_nums_taproot_input_vector(silent_payments):
    inputs = [
        (bytes.fromhex("fc8716a97a48ba9a05a98ae47b5cd201a25a7fd5d8b73c203c5f7b6b6b3b6ad7"), True),
    ]
    outpoints = [
        _outpoint("f4184fc596403b9d638783cf57adfe4c75c605f6356fbc91338530e9831e9e16", 0),
        _outpoint("a1075db55d416d3ca199f55b6084e2115b9345e16c5cf302fc80e9d5fbf5d48d", 0),
        _outpoint("a1075db55d416d3ca199f55b6084e2115b9345e16c5cf302fc80e9d5fbf5d48d", 1),
    ]
    outputs = silent_payments.create_outputs(
        inputs, outpoints, [(SCAN_KEY, SPEND_KEY)])
    assert outputs == [bytes.fromhex(
        "79e79897c52935bfd97fc6e076a6431a0c7543ca8c31e0fc3cf719bb572c842d")]


def test_bip374_official_generate_and_verify_vector(silent_payments):
    generator = bytes.fromhex(
        "02cef38f55e78b321a1f785cb1c6e33dfcef9784c18bdc4e279801c449ccdfb88e")
    secret = bytes.fromhex(
        "07ff93d43f1012a5d4a44aba55240212ed39c87b3344e46757d99f24177fc576")
    public_b = bytes.fromhex(
        "02dad4b35c2379ba8334c9a5dda8f6e6d5cd575a7cc9d3ca4faaac51839daaa30f")
    auxiliary_random = bytes.fromhex(
        "cb979b0fc8ccc7f237751e719d992fcc324b6500af33999cd54a3e5c05fb1ea4")
    message = bytes.fromhex(
        "efb07d4b382d3da1079fbf24df623ba6c2e4c764993bbfa6dd7a4fe4aaf33859")
    expected_proof = bytes.fromhex(
        "7e7e934169e0bf4706e6b29e5a621c7fe199a524744a25af80071e111c0e2e94"
        "118e730d8add118dd2ee4f7d1cc183e1b87168362d1a6f85c16d8671a3fc7a8a")
    public_a = bytes.fromhex(
        "02b540b22c2c5ef0dc886abdaad27498453d893265560bc08a187319af6f845f58")
    shared_secret = bytes.fromhex(
        "03fefe00951dcd0ef10b12523393c2b8113119de4fdeeab320694e96bdccd2775b")

    proof = silent_payments.create_dleq_proof(
        secret, public_b, auxiliary_random, generator, message)

    assert proof == expected_proof
    assert silent_payments.verify_dleq_proof(
        public_a, public_b, shared_secret, proof, generator, message)
    corrupted = proof[:-1] + bytes([proof[-1] ^ 1])
    assert not silent_payments.verify_dleq_proof(
        public_a, public_b, shared_secret, corrupted, generator, message)


def test_bip375_global_share_uses_taproot_normalization(silent_payments):
    scan_key = bytes.fromhex(
        "034bccb1c570ac1f3bc42d61fe35de605b99626501ccb20297e1acbbf2d7152aa1")
    auxiliary_random = bytes.fromhex(
        "c8d7056abd4726eb5a0f198740af14d6c1f0c16e5d7a37eaec621b661e669ac4")
    odd_secret = (6).to_bytes(32, "big")
    normalized_secret = (
        silent_payments.GROUP_ORDER - 6).to_bytes(32, "big")

    share, proof = silent_payments.create_global_ecdh_share(
        [(odd_secret, True)], scan_key, auxiliary_random)
    expected_share = silent_payments._compress_point(
        silent_payments._point_multiply(
            int.from_bytes(normalized_secret, "big"),
            silent_payments._parse_public_key(scan_key)))
    public_a = silent_payments._compress_point(
        silent_payments._generator_multiply(
            int.from_bytes(normalized_secret, "big")))

    assert share == expected_share
    assert silent_payments.verify_dleq_proof(
        public_a, scan_key, share, proof)


def test_rejects_oversized_recipient_group(silent_payments):
    with pytest.raises(ValueError, match="K_MAX"):
        silent_payments.create_outputs(
            _legacy_inputs(),
            [_outpoint("00" * 32, 0), _outpoint("01" * 32, 0)],
            [(SCAN_KEY, SPEND_KEY)] * (silent_payments.K_MAX + 1))


def test_rejects_point_at_infinity(silent_payments):
    negative_generator = (GENERATOR[0], FIELD_PRIME - GENERATOR[1])
    with pytest.raises(ValueError, match="point at infinity"):
        silent_payments._point_add(GENERATOR, negative_generator)
