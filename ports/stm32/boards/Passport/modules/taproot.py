# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: © 2020 Pieter Wuille, Jonas Nick, Tim Ruffing
# SPDX-License-Identifier: BSD-2-Clause
#
# SPDX-FileCopyrightText: © 2020 Pieter Wuille, Jonas Nick, Anthony Towns
# SPDX-License-Identifier: BSD-3-Clause
#
# taproot.py - taproot helper functions

import ubinascii
import utime
from trezorcrypto import ecdsa

# Set DEBUG to True to get a detailed debug output including
# intermediate values during key generation, signing, and
# verification. This is implemented via calls to the
# debug_print_vars() function.
#
# If you want to print values on an individual basis, use
# the pretty() function, e.g., print(pretty(foo)).
DEBUG = False

p = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
SECP256K1_ORDER = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141

# Points are tuples of X and Y coordinates and the point at infinity is
# represented by the None keyword.
G = (0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
     0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8)

# Point = Tuple[int, int]


def tagged_hash(tag, msg):
    from serializations import sha256

    tag_hash = sha256(tag.encode())
    return sha256(tag_hash + tag_hash + msg)


def hash_tap_tweak(data):
    from serializations import sha256
    from public_constants import TAP_TWEAK_SHA256
    from ubinascii import unhexlify as a2b_hex

    tag_hash = a2b_hex(TAP_TWEAK_SHA256)
    return sha256(tag_hash + tag_hash + data)


def is_infinite(P):
    return P is None


def x(P):
    assert not is_infinite(P)
    return P[0]


def y(P):
    assert not is_infinite(P)
    return P[1]


def point_add(P1, P2):

    x1 = bytes_from_int(x(P1))
    y1 = bytes_from_int(y(P1))
    x2 = bytes_from_int(x(P2))
    y2 = bytes_from_int(y(P2))

    (x3, y3) = ecdsa.point_add(x1, y1, x2, y2)
    return (int_from_bytes(x3), int_from_bytes(y3))


def scalar_multiply(n):
    n = bytes_from_int(n)
    (x, y) = ecdsa.scalar_multiply(n)
    return (int_from_bytes(x), int_from_bytes(y))


def bytes_from_int(x):
    return x.to_bytes(32, "big")


def bytes_from_point(P):
    return bytes_from_int(x(P))


def xor_bytes(b0, b1):
    return bytes(x ^ y for (x, y) in zip(b0, b1))


def lift_x(x):
    if x >= p:
        return None
    y_sq = (pow(x, 3, p) + 7) % p
    y = pow(y_sq, (p + 1) // 4, p)
    if pow(y, 2, p) != y_sq:
        return None
    return (x, y if y & 1 == 0 else p - y)


def int_from_bytes(b):
    return int.from_bytes(b, "big")


def has_even_y(P):
    assert not is_infinite(P)
    return y(P) % 2 == 0


def tweak_internal_key(internal_key, h):
    t = int_from_bytes(hash_tap_tweak(internal_key + h))
    if t >= SECP256K1_ORDER:
        raise ValueError
    P = lift_x(int_from_bytes(internal_key))
    if P is None:
        raise ValueError
    Q = point_add(P, scalar_multiply(t))
    return 0 if has_even_y(Q) else 1, bytes_from_int(x(Q))


def taproot_tweak_seckey(seckey0, h):
    seckey0 = int_from_bytes(seckey0)
    P = scalar_multiply(seckey0)
    seckey = seckey0 if has_even_y(P) else SECP256K1_ORDER - seckey0
    t = int_from_bytes(hash_tap_tweak(bytes_from_int(x(P)) + h))
    if t >= SECP256K1_ORDER:
        raise ValueError
    return bytes_from_int((seckey + t) % SECP256K1_ORDER)


def taproot_tree_helper(script_tree):
    from serializations import ser_string

    if isinstance(script_tree, tuple):
        leaf_version, script = script_tree
        h = tagged_hash("TapLeaf", bytes([leaf_version]) + ser_string(script))
        return ([((leaf_version, script), bytes())], h)
    left, left_h = taproot_tree_helper(script_tree[0])
    right, right_h = taproot_tree_helper(script_tree[1])
    ret = [(leaf, c + right_h) for leaf, c in left] + [(leaf, c + left_h) for leaf, c in right]
    if right_h < left_h:
        left_h, right_h = right_h, left_h
    return (ret, tagged_hash("TapBranch", left_h + right_h))


def output_script(internal_pubkey, script_tree):
    """Given a internal public key and a tree of scripts, compute the output script.
    script_tree is either:
     - a (leaf_version, script) tuple (leaf_version is 0xc0 for [[bip-0342.mediawiki|BIP342]] scripts)
     - a list of two elements, each with the same structure as script_tree itself
     - None
    """
    if script_tree is None:
        h = bytes()
    else:
        _, h = taproot_tree_helper(script_tree)
    _, output_pubkey = tweak_internal_key(internal_pubkey, h)
    return bytes([0x51, 0x20]) + output_pubkey


def taproot_sign_key(script_tree, internal_seckey, hash_type, sighash):
    from foundation import secp256k1

    if script_tree is None:
        h = bytes()
    else:
        _, h = taproot_tree_helper(script_tree)
    output_seckey = taproot_tweak_seckey(internal_seckey, h)
    sig = secp256k1.schnorr_sign(sighash, output_seckey)
    if hash_type != 0:
        sig += bytes([hash_type])
    return sig


def taproot_sign_script(internal_pubkey, script_tree, script_num, inputs):
    info, h = taproot_tree_helper(script_tree)
    (leaf_version, script), path = info[script_num]
    output_pubkey_y_parity, _ = tweak_internal_key(internal_pubkey, h)
    pubkey_data = bytes([output_pubkey_y_parity + leaf_version]) + internal_pubkey
    return inputs + [script, pubkey_data + path]
