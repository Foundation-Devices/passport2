# TODO: add BSD-2-Clause license for BIP340 and BSD-3-Clase for BIP341

import ubinascii
import utime

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

# This implementation can be sped up by storing the midstate after hashing
# tag_hash instead of rehashing it all the time.
# def tagged_hash(tag, msg) -> bytes:
#     tag_hash = uhashlib.sha256(tag.encode()).digest()
#     return uhashlib.sha256(tag_hash + tag_hash + msg).digest()


# TODO: optimize for TapTweak
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
    if P1 is None:
        return P2
    if P2 is None:
        return P1
    if (x(P1) == x(P2)) and (y(P1) != y(P2)):
        return None
    if P1 == P2:
        lam = (3 * x(P1) * x(P1) * pow(2 * y(P1), p - 2, p)) % p
    else:
        lam = ((y(P2) - y(P1)) * pow(x(P2) - x(P1), p - 2, p)) % p
    x3 = (lam * lam - x(P1) - x(P2)) % p
    return (x3, (lam * (x(P1) - x3) - y(P1)) % p)


def point_mul(P, n):
    R = None
    for i in range(256):
        if (n >> i) & 1:
            R = point_add(R, P)
        P = point_add(P, P)
    return R


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
    print("1 {}".format(utime.ticks_ms()))
    t = int_from_bytes(hash_tap_tweak(internal_key + h))
    print("2 {}".format(utime.ticks_ms()))
    if t >= SECP256K1_ORDER:
        raise ValueError
    print("3 {}".format(utime.ticks_ms()))
    P = lift_x(int_from_bytes(internal_key))
    print("4 {}".format(utime.ticks_ms()))
    if P is None:
        raise ValueError
    print("5 {}".format(utime.ticks_ms()))
    Q = point_add(P, point_mul(G, t))
    print("6 {}".format(utime.ticks_ms()))
    return 0 if has_even_y(Q) else 1, bytes_from_int(x(Q))


# def taproot_tweak_seckey(seckey0, h):
#     seckey0 = int_from_bytes(seckey0)
#     P = point_mul(G, seckey0)
#     seckey = seckey0 if has_even_y(P) else SECP256K1_ORDER - seckey0
#     t = int_from_bytes(tagged_hash("TapTweak", bytes_from_int(x(P)) + h))
#     if t >= SECP256K1_ORDER:
#         raise ValueError
#     return bytes_from_int((seckey + t) % SECP256K1_ORDER)
#
#
# def taproot_tree_helper(script_tree):
#     if isinstance(script_tree, tuple):
#         leaf_version, script = script_tree
#         h = tagged_hash("TapLeaf", bytes([leaf_version]) + ser_script(script))
#         return ([((leaf_version, script), bytes())], h)
#     left, left_h = taproot_tree_helper(script_tree[0])
#     right, right_h = taproot_tree_helper(script_tree[1])
#     ret = [(l, c + right_h) for l, c in left] + [(l, c + left_h) for l, c in right]
#     if right_h < left_h:
#         left_h, right_h = right_h, left_h
#     return (ret, tagged_hash("TapBranch", left_h + right_h))
#
#
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