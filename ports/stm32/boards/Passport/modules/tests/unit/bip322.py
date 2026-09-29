# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Test BIP-322 Taproot message signing.

from foundation import secp256k1
from ubinascii import a2b_base64
from ubinascii import unhexlify as a2b_hex

from bip322 import create_virtual_transactions, sign_taproot_simple, taproot_signature_hash
from serializations import hash256
from taproot import output_script, tagged_hash


# A BIP-340 verifier, implemented here so the generated signature is checked
# against an implementation independent of the one that produced it. Passport
# builds with FOUNDATION_ADDITIONS, so trezorcrypto.bip340 is compiled out, and
# foundation.secp256k1 exposes signing but no verification.
P_FIELD = (1 << 256) - (1 << 32) - 977
N_ORDER = 0xfffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141
G_POINT = (0x79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798,
           0x483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8)


def lift_x(x):
    if x >= P_FIELD:
        return None

    y_sq = (pow(x, 3, P_FIELD) + 7) % P_FIELD
    y = pow(y_sq, (P_FIELD + 1) // 4, P_FIELD)
    if pow(y, 2, P_FIELD) != y_sq:
        return None

    return (x, y if y % 2 == 0 else P_FIELD - y)


def point_add(p1, p2):
    if p1 is None:
        return p2
    if p2 is None:
        return p1
    if p1[0] == p2[0] and p1[1] != p2[1]:
        return None

    if p1 == p2:
        lam = (3 * p1[0] * p1[0] * pow(2 * p1[1], P_FIELD - 2, P_FIELD)) % P_FIELD
    else:
        lam = ((p2[1] - p1[1]) * pow(p2[0] - p1[0], P_FIELD - 2, P_FIELD)) % P_FIELD

    x = (lam * lam - p1[0] - p2[0]) % P_FIELD
    return (x, (lam * (p1[0] - x) - p1[1]) % P_FIELD)


def point_mul(point, scalar):
    result = None
    for i in range(256):
        if (scalar >> i) & 1:
            result = point_add(result, point)
        point = point_add(point, point)
    return result


def bip340_verify(pubkey, signature, digest):
    point = lift_x(int.from_bytes(pubkey, 'big'))
    if point is None:
        return False

    r = int.from_bytes(signature[:32], 'big')
    s = int.from_bytes(signature[32:], 'big')
    if r >= P_FIELD or s >= N_ORDER:
        return False

    challenge = tagged_hash('BIP0340/challenge', signature[:32] + pubkey + digest)
    e = int.from_bytes(challenge, 'big') % N_ORDER

    computed = point_add(point_mul(G_POINT, s), point_mul(point, N_ORDER - e))
    if computed is None or computed[1] % 2 != 0 or computed[0] != r:
        return False

    return True


# Check the verifier itself against a plain sign/verify round trip first, so a
# broken verifier cannot silently pass the BIP-322 assertions below.
probe_key = a2b_hex('01' * 32)
probe_pubkey = secp256k1.public_key_schnorr(probe_key)
probe_digest = a2b_hex('02' * 32)
probe_signature = secp256k1.sign_schnorr(probe_digest, probe_key)

assert bip340_verify(probe_pubkey, probe_signature, probe_digest)
assert not bip340_verify(probe_pubkey, probe_signature, a2b_hex('03' * 32))


# BIP-322 basic test vector for the virtual transaction construction.
message = b'Hello World'
message_challenge = a2b_hex('00142b05d564e6a7a33c087f16e0f730d1440123799d')
to_spend, to_sign = create_virtual_transactions(message, message_challenge)

assert hash256(to_spend)[::-1] == a2b_hex(
    'b79d196740ad5217771c1098fc4a4b51e0535c32236c71f1ea4d61a2d603352b'
)
assert hash256(to_sign)[::-1] == a2b_hex(
    '88737ae86f2077145f93cc4b153ae9a1cb8d56afa511988c149c5c8c9d93bddf'
)

# BIP-322 generated P2TR test vector.
message = b'PURVOQ544B6HUATVBJZN5EZJUU'
message_challenge = a2b_hex('5120c038cb8c0c783475d76fba41a5866f7e80385898f10609855c20d2aced117127')
private_key = a2b_hex('f805d22c9379f60b87770c8358c8fc2310b3e65d1c4555a51f58c912862b385b')
internal_pubkey = secp256k1.public_key_schnorr(private_key)

assert output_script(internal_pubkey, None) == message_challenge
assert taproot_signature_hash(message, message_challenge) == a2b_hex(
    '7f9ffcd78cf3111b2ff6ede58671348f25bfc9ac64a4ca44570944cb9f7df734'
)

signature = sign_taproot_simple(message, internal_pubkey, private_key)
assert signature.startswith('smp')

witness = a2b_base64(signature[3:])
assert len(witness) == 66
assert witness[:2] == b'\x01\x40'

# The encoding checks above pass for any 64-byte signature, so verify the
# signature cryptographically as well.
schnorr_signature = witness[2:]
output_pubkey = message_challenge[2:]
sighash = taproot_signature_hash(message, message_challenge)

assert bip340_verify(output_pubkey, schnorr_signature, sighash)

# It must bind to the message.
tampered_sighash = taproot_signature_hash(b'Tampered message', message_challenge)
assert tampered_sighash != sighash
assert not bip340_verify(output_pubkey, schnorr_signature, tampered_sighash)

# And it must be made with the tweaked output key, not the internal key. Both
# are valid x-only keys, so only verification distinguishes them.
assert internal_pubkey != output_pubkey
assert not bip340_verify(internal_pubkey, schnorr_signature, sighash)

return_value.write(b'OK')
