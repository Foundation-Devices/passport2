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


def _legacy_inputs():
    return [
        (bytes.fromhex("eadc78165ff1f8ea94ad7cfdc54990738a4c53f6e0507b42154201b8e5dff3b1"), False),
        (bytes.fromhex("93f5ed907ad5b2bdbbdcb5d9116ebc0a4e1f92f910d5260237fa45a9408aad16"), False),
    ]


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
