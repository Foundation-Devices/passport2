# SPDX-FileCopyrightText: 2026 The Passport contributors
# SPDX-License-Identifier: GPL-3.0-or-later

"""BIP352 sender-side output derivation helpers."""

import trezorcrypto
from foundation import secp256k1
from trezorcrypto import ecdsa


FIELD_PRIME = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
GROUP_ORDER = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
K_MAX = 2323
BECH32M_CONST = 0x2BC830A3
_BECH32_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
_BECH32_GENERATORS = (0x3B6A57B2, 0x26508E6D, 0x1EA119FA,
                      0x3D4233DD, 0x2A1462B3)
GENERATOR_PUBLIC_KEY = bytes.fromhex(
    "0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798")


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


def _bech32_polymod(values):
    checksum = 1
    for value in values:
        top = checksum >> 25
        checksum = ((checksum & 0x1FFFFFF) << 5) ^ value
        for index, generator in enumerate(_BECH32_GENERATORS):
            if (top >> index) & 1:
                checksum ^= generator
    return checksum


def _bech32_hrp_expand(hrp):
    return ([ord(char) >> 5 for char in hrp] + [0] +
            [ord(char) & 31 for char in hrp])


def _convert_bits(values, from_bits, to_bits, pad):
    accumulator = 0
    bit_count = 0
    result = []
    max_value = (1 << to_bits) - 1
    max_accumulator = (1 << (from_bits + to_bits - 1)) - 1

    for value in values:
        if value < 0 or value >> from_bits:
            raise ValueError("invalid bech32 data value")
        accumulator = ((accumulator << from_bits) | value) & max_accumulator
        bit_count += from_bits
        while bit_count >= to_bits:
            bit_count -= to_bits
            result.append((accumulator >> bit_count) & max_value)

    if pad:
        if bit_count:
            result.append((accumulator << (to_bits - bit_count)) & max_value)
    elif bit_count >= from_bits or \
            ((accumulator << (to_bits - bit_count)) & max_value):
        raise ValueError("invalid bech32 padding")

    return bytes(result)


def decode_address(address, expected_hrp=None):
    """Decode a BIP352 address into ``(hrp, version, scan_key, spend_key)``."""

    if not isinstance(address, str) or not address or len(address) > 1023:
        raise ValueError("invalid silent payment address length")
    if address.lower() != address and address.upper() != address:
        raise ValueError("mixed-case silent payment address")

    address = address.lower()
    separator = address.rfind("1")
    if separator < 1 or separator + 7 > len(address):
        raise ValueError("invalid silent payment address separator")

    hrp = address[:separator]
    if hrp not in ("sp", "tsp"):
        raise ValueError("invalid silent payment address network")
    if expected_hrp is not None and hrp != expected_hrp:
        raise ValueError("silent payment address network mismatch")

    try:
        data = [_BECH32_CHARSET.index(char) for char in address[separator + 1:]]
    except ValueError:
        raise ValueError("invalid character in silent payment address")
    if _bech32_polymod(_bech32_hrp_expand(hrp) + data) != BECH32M_CONST:
        raise ValueError("invalid silent payment address checksum")

    payload = data[:-6]
    if not payload:
        raise ValueError("missing silent payment address version")
    version = payload[0]
    if version == 31:
        raise ValueError("unsupported silent payment address version")

    key_data = _convert_bits(payload[1:], 5, 8, False)
    if version == 0 and len(key_data) != 66:
        raise ValueError("version 0 silent payment address must contain 66 key bytes")
    if version > 0 and len(key_data) < 66:
        raise ValueError("silent payment address key data is too short")

    scan_public_key = key_data[:33]
    spend_public_key = key_data[33:66]
    _parse_public_key(scan_public_key)
    _parse_public_key(spend_public_key)
    return hrp, version, scan_public_key, spend_public_key


def create_output_scripts_from_psbt(psbt, addresses, sensitive_values,
                                    expected_hrp=None):
    """Derive BIP352 P2TR scripts for a validated, single-owner PSBT.

    ``psbt.consider_inputs()`` must have run so each input has a verified
    signing key. Eligible inputs owned by another signer are rejected because
    their private keys are required for the aggregate sender key.
    """

    import stash
    from taproot import taproot_tweak_seckey
    from utils import keypath_to_str, swab32

    recipients = []
    for address in addresses:
        _, _, scan_key, spend_key = decode_address(address, expected_hrp)
        recipients.append((scan_key, spend_key))

    outpoints = []
    input_private_keys = []
    try:
        for input_index, txin in psbt.input_iter():
            outpoints.append(txin.prevout.serialize())
            psbt_input = psbt.inputs[input_index]
            if not psbt_input.has_utxo():
                raise ValueError("silent payment input is missing its UTXO")

            utxo = psbt_input.get_utxo(txin.prevout.n)
            address_type, _, is_segwit = utxo.get_address()
            is_taproot = address_type == "p2tr"

            if address_type == "p2pkh":
                is_eligible = True
            elif address_type == "p2sh":
                redeem_script = (psbt_input.get(psbt_input.redeem_script)
                                 if psbt_input.redeem_script else None)
                is_eligible = (not is_segwit and
                               redeem_script is not None and
                               len(redeem_script) == 22 and
                               redeem_script[:2] == b"\x00\x14")
            elif address_type == "p2tr":
                is_eligible = True
            else:
                # P2PK and multisig inputs are excluded by BIP352.
                is_eligible = False

            if not is_eligible:
                continue

            which_key = psbt_input.required_key
            if not isinstance(which_key, bytes):
                raise ValueError(
                    "silent payment eligible input is not controlled by Passport")

            if is_taproot:
                path_info = psbt_input.tap_subpaths.get(which_key)
                if path_info is None or path_info[1]:
                    raise ValueError("unsupported taproot silent payment input")
                path = path_info[0]
            else:
                path = psbt_input.subpaths.get(which_key)

            if not path or path[0] not in (psbt.my_xfp, swab32(psbt.my_xfp)):
                raise ValueError("silent payment input path does not belong to Passport")

            node = sensitive_values.derive_path(
                keypath_to_str(path), register=False)
            raw_private_key = None
            try:
                public_key = node.public_key()
                expected_public_key = public_key[1:] if is_taproot else public_key
                if expected_public_key != which_key:
                    raise ValueError("silent payment input path produced wrong key")

                raw_private_key = node.private_key()
                if is_taproot:
                    output_private_key = taproot_tweak_seckey(
                        raw_private_key, bytes())
                    stash.blank_object(raw_private_key)
                    raw_private_key = None
                else:
                    output_private_key = raw_private_key
                    raw_private_key = None

                input_private_keys.append((output_private_key, is_taproot))
            finally:
                if raw_private_key is not None:
                    stash.blank_object(raw_private_key)
                stash.blank_object(node)

        output_keys = create_outputs(
            input_private_keys, outpoints, recipients)
        return [b"\x51\x20" + output_key for output_key in output_keys]
    finally:
        for private_key, _ in input_private_keys:
            stash.blank_object(private_key)


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


def _point_subtract(left, right):
    return _point_add(left, (right[0], FIELD_PRIME - right[1]))


def _optional_point_multiply(scalar, point):
    scalar %= GROUP_ORDER
    if scalar == 0:
        return None
    return _point_multiply(scalar, point)


def _optional_point_subtract(left, right):
    if left is None:
        if right is None:
            return None
        return right[0], FIELD_PRIME - right[1]
    if right is None:
        return left
    return _point_subtract(left, right)


def _normalize_input_key(secret_key, is_taproot):
    scalar = _checked_scalar(secret_key)
    if is_taproot and (_generator_multiply(scalar)[1] & 1):
        scalar = GROUP_ORDER - scalar
    return scalar


def _aggregate_input_key(input_private_keys):
    aggregate_key = 0
    for secret_key, is_taproot in input_private_keys:
        aggregate_key = (aggregate_key +
                         _normalize_input_key(secret_key, is_taproot)) % GROUP_ORDER
    if aggregate_key == 0:
        raise ValueError("aggregate input private key is zero")
    return aggregate_key


def create_dleq_proof(secret_key, public_key, auxiliary_random=None,
                      generator=GENERATOR_PUBLIC_KEY, message=None):
    """Create a BIP374 proof that ``a*G`` and ``a*B`` share secret ``a``."""

    secret = _checked_scalar(secret_key)
    public_point = _parse_public_key(public_key)
    generator_point = _parse_public_key(generator)
    if message is None:
        message = bytes()
    elif len(message) not in (0, 32):
        raise ValueError("BIP374 message must contain 32 bytes")
    if auxiliary_random is None:
        auxiliary_random = trezorcrypto.random.bytes(32)
    if len(auxiliary_random) != 32:
        raise ValueError("BIP374 auxiliary random data must contain 32 bytes")

    secret_bytes = _bytes32(secret)
    public_a = _point_multiply(secret, generator_point)
    shared_secret = _point_multiply(secret, public_point)
    auxiliary_hash = _tagged_hash("BIP0374/aux", auxiliary_random)
    masked_secret = bytes(
        left ^ right for left, right in zip(secret_bytes, auxiliary_hash))
    nonce = int.from_bytes(_tagged_hash(
        "BIP0374/nonce",
        masked_secret + _compress_point(public_a) +
        _compress_point(shared_secret) + message), "big") % GROUP_ORDER
    if nonce == 0:
        raise ValueError("BIP374 nonce is zero")

    nonce_g = _point_multiply(nonce, generator_point)
    nonce_b = _point_multiply(nonce, public_point)
    challenge = int.from_bytes(_tagged_hash(
        "BIP0374/challenge",
        _compress_point(public_a) + _compress_point(public_point) +
        _compress_point(shared_secret) + _compress_point(generator_point) +
        _compress_point(nonce_g) + _compress_point(nonce_b) + message), "big")
    response = (nonce + challenge * secret) % GROUP_ORDER
    proof = _bytes32(challenge) + _bytes32(response)

    if not verify_dleq_proof(
            _compress_point(public_a), public_key,
            _compress_point(shared_secret), proof, generator, message):
        raise ValueError("generated BIP374 proof did not verify")
    return proof


def verify_dleq_proof(public_a, public_b, shared_secret, proof,
                      generator=GENERATOR_PUBLIC_KEY, message=None):
    """Return whether a BIP374 discrete-log equality proof is valid."""

    try:
        if len(proof) != 64:
            return False
        if message is None:
            message = bytes()
        elif len(message) not in (0, 32):
            return False

        point_a = _parse_public_key(public_a)
        point_b = _parse_public_key(public_b)
        point_c = _parse_public_key(shared_secret)
        generator_point = _parse_public_key(generator)
        challenge = int.from_bytes(proof[:32], "big")
        response = int.from_bytes(proof[32:], "big")
        if response >= GROUP_ORDER:
            return False

        nonce_g = _optional_point_subtract(
            _optional_point_multiply(response, generator_point),
            _optional_point_multiply(challenge, point_a))
        nonce_b = _optional_point_subtract(
            _optional_point_multiply(response, point_b),
            _optional_point_multiply(challenge, point_c))
        if nonce_g is None or nonce_b is None:
            return False
        expected = int.from_bytes(_tagged_hash(
            "BIP0374/challenge",
            _compress_point(point_a) + _compress_point(point_b) +
            _compress_point(point_c) + _compress_point(generator_point) +
            _compress_point(nonce_g) + _compress_point(nonce_b) + message), "big")
        return challenge == expected
    except (TypeError, ValueError):
        return False


def create_global_ecdh_share(input_private_keys, scan_public_key,
                             auxiliary_random=None):
    """Create the BIP375 global ECDH share and matching BIP374 proof."""

    aggregate_key = _aggregate_input_key(input_private_keys)
    scan_point = _parse_public_key(scan_public_key)
    share = _compress_point(_point_multiply(aggregate_key, scan_point))
    proof = create_dleq_proof(
        _bytes32(aggregate_key), scan_public_key, auxiliary_random)
    return share, proof


def create_bip375_output_scripts(input_private_keys, outpoints, output_info):
    """Return BIP375 output scripts keyed by their original PSBT output index.

    ``output_info`` contains ``(output_index, scan_key || spend_key)`` pairs.
    BIP375 assigns ``k`` after sorting codes that share a scan key, with
    duplicate codes ordered by their PSBT output index.
    """

    ordered = []
    seen_indexes = set()
    for output_index, info in output_info:
        if not isinstance(output_index, int) or output_index < 0:
            raise ValueError("invalid BIP375 output index")
        if output_index in seen_indexes:
            raise ValueError("duplicate BIP375 output index")
        if len(info) != 66:
            raise ValueError("BIP375 output info must contain 66 bytes")
        scan_key = info[:33]
        spend_key = info[33:]
        _parse_public_key(scan_key)
        _parse_public_key(spend_key)
        ordered.append((scan_key, spend_key, output_index))
        seen_indexes.add(output_index)

    if not ordered:
        raise ValueError("at least one BIP375 output is required")

    ordered.sort(key=lambda item: (item[0], item[1], item[2]))
    recipients = [(scan_key, spend_key)
                  for scan_key, spend_key, _ in ordered]
    scripts = create_outputs(input_private_keys, outpoints, recipients)
    return {item[2]: b"\x51\x20" + script
            for item, script in zip(ordered, scripts)}


def verify_bip375_output_scripts(input_private_keys, outpoints, output_info,
                                 output_scripts):
    """Verify every silent-payment PSBT output script and reject extras."""

    expected = create_bip375_output_scripts(
        input_private_keys, outpoints, output_info)
    if set(output_scripts) != set(expected):
        return False
    return all(output_scripts[index] == script
               for index, script in expected.items())


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

    aggregate_key = _aggregate_input_key(input_private_keys)

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
