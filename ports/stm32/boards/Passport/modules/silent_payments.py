# SPDX-FileCopyrightText: 2026 The Passport contributors
# SPDX-License-Identifier: GPL-3.0-or-later

"""BIP352 sender-side output derivation helpers."""

import trezorcrypto
from foundation import secp256k1
from trezorcrypto import ecdsa


FIELD_PRIME = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
GROUP_ORDER = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
K_MAX = 2323


def _bytes32(value):
    return value.to_bytes(32, "big")


def _tagged_hash(tag, message):
    tag_hash = trezorcrypto.sha256(tag.encode()).digest()
    return trezorcrypto.sha256(tag_hash + tag_hash + message).digest()


def _checked_scalar(value):
    scalar = int.from_bytes(value, "big")
    if scalar == 0 or scalar >= GROUP_ORDER:
        raise ValueError("invalid secp256k1 scalar")
    return scalar


def _lift_x(x_coord):
    if x_coord >= FIELD_PRIME:
        raise ValueError("invalid secp256k1 x coordinate")

    y_squared = (pow(x_coord, 3, FIELD_PRIME) + 7) % FIELD_PRIME
    y_coord = pow(y_squared, (FIELD_PRIME + 1) // 4, FIELD_PRIME)
    if pow(y_coord, 2, FIELD_PRIME) != y_squared:
        raise ValueError("public key is not on secp256k1")
    if y_coord & 1:
        y_coord = FIELD_PRIME - y_coord
    return x_coord, y_coord


def _parse_public_key(public_key):
    if len(public_key) == 33 and public_key[0] in (2, 3):
        point = _lift_x(int.from_bytes(public_key[1:], "big"))
        if (point[1] & 1) != (public_key[0] & 1):
            point = point[0], FIELD_PRIME - point[1]
        return point

    if len(public_key) == 65 and public_key[0] == 4:
        point = (int.from_bytes(public_key[1:33], "big"),
                 int.from_bytes(public_key[33:], "big"))
        if point[0] >= FIELD_PRIME or point[1] >= FIELD_PRIME:
            raise ValueError("invalid secp256k1 public key")
        if (pow(point[1], 2, FIELD_PRIME) -
                (pow(point[0], 3, FIELD_PRIME) + 7)) % FIELD_PRIME:
            raise ValueError("public key is not on secp256k1")
        return point

    raise ValueError("public key must be compressed or uncompressed")


def _compress_point(point):
    return bytes([2 | (point[1] & 1)]) + _bytes32(point[0])


def _generator_multiply(scalar):
    x_coord, y_coord = ecdsa.scalar_multiply(_bytes32(scalar))
    return int.from_bytes(x_coord, "big"), int.from_bytes(y_coord, "big")


def _point_add(left, right):
    if left[0] == right[0] and (left[1] + right[1]) % FIELD_PRIME == 0:
        raise ValueError("point addition produced the point at infinity")
    x_coord, y_coord = ecdsa.point_add(
        _bytes32(left[0]), _bytes32(left[1]),
        _bytes32(right[0]), _bytes32(right[1]))
    return int.from_bytes(x_coord, "big"), int.from_bytes(y_coord, "big")


def _point_multiply(scalar, point):
    result = secp256k1.multiply(_bytes32(scalar), _compress_point(point))
    return _parse_public_key(result)


def _normalize_input_key(secret_key, is_taproot):
    scalar = _checked_scalar(secret_key)
    if is_taproot and (_generator_multiply(scalar)[1] & 1):
        scalar = GROUP_ORDER - scalar
    return scalar


def create_outputs_with_shared_secrets(input_private_keys, outpoints, recipients):
    """Derive BIP352 x-only outputs and compressed ECDH shared secrets.

    ``input_private_keys`` contains ``(32-byte secret, is_taproot)`` tuples.
    ``outpoints`` contains serialized 36-byte Bitcoin outpoints.
    ``recipients`` contains ordered ``(scan_pubkey, spend_pubkey)`` tuples.
    Recipient ordering is significant for multiple labels sharing a scan key.
    """

    if not input_private_keys or not outpoints:
        raise ValueError("input keys and outpoints must be non-empty")
    if not recipients:
        raise ValueError("at least one recipient is required")
    if any(len(outpoint) != 36 for outpoint in outpoints):
        raise ValueError("outpoints must use 36-byte Bitcoin serialization")

    aggregate_key = 0
    for secret_key, is_taproot in input_private_keys:
        aggregate_key = (aggregate_key +
                         _normalize_input_key(secret_key, is_taproot)) % GROUP_ORDER
    if aggregate_key == 0:
        raise ValueError("aggregate input private key is zero")

    aggregate_public_key = _generator_multiply(aggregate_key)
    input_hash = _checked_scalar(_tagged_hash(
        "BIP0352/Inputs",
        min(outpoints) + _compress_point(aggregate_public_key)))

    groups = []
    group_indexes = {}
    for scan_public_key, spend_public_key in recipients:
        scan_point = _parse_public_key(scan_public_key)
        spend_point = _parse_public_key(spend_public_key)
        scan_key = _compress_point(scan_point)
        index = group_indexes.get(scan_key)
        if index is None:
            index = len(groups)
            group_indexes[scan_key] = index
            groups.append([scan_point, []])
        groups[index][1].append(spend_point)
        if len(groups[index][1]) > K_MAX:
            raise ValueError("silent payment recipient group exceeds K_MAX")

    outputs = []
    shared_secrets = []
    ecdh_scalar = (input_hash * aggregate_key) % GROUP_ORDER
    if ecdh_scalar == 0:
        raise ValueError("invalid ECDH scalar")

    for scan_point, spend_points in groups:
        shared_secret = _point_multiply(ecdh_scalar, scan_point)
        compressed_secret = _compress_point(shared_secret)
        shared_secrets.append(compressed_secret)

        for output_index, spend_point in enumerate(spend_points):
            tweak = _checked_scalar(_tagged_hash(
                "BIP0352/SharedSecret",
                compressed_secret + output_index.to_bytes(4, "big")))
            output_point = _point_add(spend_point, _generator_multiply(tweak))
            outputs.append(_bytes32(output_point[0]))

    return outputs, shared_secrets


def create_outputs(input_private_keys, outpoints, recipients):
    outputs, _ = create_outputs_with_shared_secrets(
        input_private_keys, outpoints, recipients)
    return outputs
