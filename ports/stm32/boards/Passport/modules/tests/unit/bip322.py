# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Test BIP-322 Taproot message signing.

from foundation import secp256k1
from ubinascii import a2b_base64
from ubinascii import unhexlify as a2b_hex
from uio import BytesIO
from ustruct import pack

from bip322 import INVALID_REQUEST, TAPROOT_ONLY, create_virtual_transactions, read_signing_request
from bip322 import sign_taproot_request, sign_taproot_simple, taproot_signature_hash
from serializations import SIGHASH_ALL, SIGHASH_DEFAULT, deser_compact_size, hash256, ser_string
from taproot import output_script, tagged_hash


def reverse_bytes(data):
    # Transaction ids are displayed least-significant byte first. MicroPython
    # has no slices with a step, so data[::-1] is not available here.
    out = bytearray(len(data))
    for i in range(len(data)):
        out[len(data) - 1 - i] = data[i]
    return bytes(out)


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

assert reverse_bytes(hash256(to_spend)) == a2b_hex(
    'b79d196740ad5217771c1098fc4a4b51e0535c32236c71f1ea4d61a2d603352b'
)
assert reverse_bytes(hash256(to_sign)) == a2b_hex(
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

# Text signatures are SIGHASH_ALL, which every verifier must accept and the only type Sparrow accepts.
witness = a2b_base64(signature[3:])
assert len(witness) == 67
assert witness[:2] == b'\x01\x41'
assert witness[66] == SIGHASH_ALL

# SIGHASH_ALL changes the digest. The value comes from an implementation outside the firmware, checked against
# the BIP-322 SIGHASH_DEFAULT vector above.
sighash = taproot_signature_hash(message, message_challenge)
sighash_all = taproot_signature_hash(message, message_challenge, SIGHASH_ALL)
assert sighash_all == a2b_hex('f4ee2b0fa213cd562b51dcaa94cae4d16d39256ee52a754779222eaddf4184f3')

# The encoding checks above pass for any 65-byte signature, so verify the
# signature cryptographically as well.
schnorr_signature = witness[2:66]
output_pubkey = message_challenge[2:]

assert bip340_verify(output_pubkey, schnorr_signature, sighash_all)
assert not bip340_verify(output_pubkey, schnorr_signature, sighash)

# It must bind to the message.
tampered_sighash = taproot_signature_hash(b'Tampered message', message_challenge, SIGHASH_ALL)
assert tampered_sighash != sighash_all
assert not bip340_verify(output_pubkey, schnorr_signature, tampered_sighash)

# And it must be made with the tweaked output key, not the internal key. Both
# are valid x-only keys, so only verification distinguishes them.
assert internal_pubkey != output_pubkey
assert not bip340_verify(internal_pubkey, schnorr_signature, sighash_all)


# BIP-322 requests sent as a PSBT, built the way Sparrow builds them: the to_sign transaction as a PSBTv0,
# the message in global field 0x09, and an input carrying the zero-value UTXO, SIGHASH_ALL and the
# key-path derivation.
HARDENED = 0x80000000
XFP = 0x78563412
PATH = [86 | HARDENED, 1 | HARDENED, HARDENED, 0, 0]


def derivation(path=PATH, leaves=0):
    return bytes([leaves]) + b'\x11' * 32 * leaves + pack('<%dI' % (1 + len(path)), XFP, *path)


def request_maps(message, script):
    _, to_sign = create_virtual_transactions(message, script)
    global_map = [(b'\x00', to_sign), (b'\x09', message)]
    input_map = [(b'\x01', pack('<q', 0) + ser_string(script)),
                 (b'\x03', pack('<I', SIGHASH_ALL)),
                 (b'\x16' + internal_pubkey, derivation()),
                 (b'\x17', internal_pubkey)]
    return global_map, input_map, []


def serialize(maps, tail=b''):
    out = b'psbt\xff'
    for entries in maps:
        for key, value in entries:
            out += ser_string(key) + ser_string(value)
        out += b'\x00'
    return out + tail


def read_maps(data):
    fd = BytesIO(data)
    assert fd.read(5) == b'psbt\xff'
    maps = []
    for _ in range(3):
        entries = []
        while True:
            key = fd.read(deser_compact_size(fd))
            if not key:
                break
            entries.append((key, fd.read(deser_compact_size(fd))))
        maps.append(entries)
    assert fd.read(1) == b''
    return maps


def rejected(psbt, error):
    try:
        read_signing_request(psbt)
    except ValueError as e:
        assert str(e) == error, str(e)
        return
    assert False, 'request was accepted'


other_key = a2b_hex('01' * 32)
other_pubkey = secp256k1.public_key_schnorr(other_key)

# A request reads back with its message, address, key derivation and sighash type.
maps = request_maps(message, message_challenge)
psbt = serialize(maps)
request = read_signing_request(psbt)
assert request.message == message
assert request.script_pubkey == message_challenge
assert request.xfp == XFP
assert request.path == PATH
assert request.hash_type == SIGHASH_ALL

# Signing adds the key-path signature to the input and changes nothing else.
signed = read_maps(sign_taproot_request(request, internal_pubkey, private_key))
assert signed[0] == maps[0]
assert signed[1][:-1] == maps[1]
assert signed[2] == maps[2]
key, tap_key_sig = signed[1][-1]
assert key == b'\x13'
assert len(tap_key_sig) == 65
assert tap_key_sig[64] == SIGHASH_ALL
assert bip340_verify(output_pubkey, tap_key_sig[:64], sighash_all)
assert not bip340_verify(output_pubkey, tap_key_sig[:64], sighash)
rejected(serialize(signed), 'This message request is already signed.')

# Without a sighash type, a request is signed with SIGHASH_DEFAULT, the Taproot default for PSBTs.
global_map, input_map, output_map = request_maps(message, message_challenge)
del input_map[1]
request = read_signing_request(serialize((global_map, input_map, output_map)))
assert request.hash_type == SIGHASH_DEFAULT
tap_key_sig = read_maps(sign_taproot_request(request, internal_pubkey, private_key))[1][-1][1]
assert len(tap_key_sig) == 64
assert bip340_verify(output_pubkey, tap_key_sig, sighash)

# A key that does not own the address does not sign.
try:
    sign_taproot_request(request, other_pubkey, other_key)
    assert False, 'signed with the wrong key'
except ValueError:
    pass

# The message under review must be the one the transaction commits to, and so must the address.
MISMATCH = 'The transaction in this request does not match its message.'
global_map, input_map, output_map = request_maps(message, message_challenge)
global_map[1] = (b'\x09', b'Tampered message')
rejected(serialize((global_map, input_map, output_map)), MISMATCH)

global_map, input_map, output_map = request_maps(message, message_challenge)
input_map[0] = (b'\x01', pack('<q', 0) + ser_string(output_script(other_pubkey, None)))
rejected(serialize((global_map, input_map, output_map)), MISMATCH)

# The output being spent holds no value.
global_map, input_map, output_map = request_maps(message, message_challenge)
input_map[0] = (b'\x01', pack('<q', 1) + ser_string(message_challenge))
rejected(serialize((global_map, input_map, output_map)), INVALID_REQUEST)

# Other address types are pointed to the Electrum format.
p2wpkh_request = serialize(request_maps(b'Hello World', a2b_hex('00142b05d564e6a7a33c087f16e0f730d1440123799d')))
rejected(p2wpkh_request, TAPROOT_ONLY)

# The message has to be in the request.
global_map, input_map, output_map = request_maps(message, message_challenge)
del global_map[1]
rejected(serialize((global_map, input_map, output_map)), 'This request does not include the message to sign.')

# Only SIGHASH_DEFAULT and SIGHASH_ALL commit to the whole virtual transaction.
for hash_type in (2, 3, 0x81):
    global_map, input_map, output_map = request_maps(message, message_challenge)
    input_map[1] = (b'\x03', pack('<I', hash_type))
    rejected(serialize((global_map, input_map, output_map)), 'Unsupported signature hash type.')

# Exactly one key-path derivation below a master fingerprint.
for bad_derivation in (derivation(leaves=1), derivation(path=[]), derivation()[:-2]):
    global_map, input_map, output_map = request_maps(message, message_challenge)
    input_map[2] = (input_map[2][0], bad_derivation)
    rejected(serialize((global_map, input_map, output_map)), INVALID_REQUEST)

global_map, input_map, output_map = request_maps(message, message_challenge)
input_map.append((b'\x16' + other_pubkey, derivation()))
rejected(serialize((global_map, input_map, output_map)), INVALID_REQUEST)

global_map, input_map, output_map = request_maps(message, message_challenge)
del input_map[2]
rejected(serialize((global_map, input_map, output_map)), INVALID_REQUEST)

# Malformed PSBTs: a duplicate key, an extra map, a truncated or mislabelled stream, and a PSBTv2 with no
# unsigned transaction.
global_map, input_map, output_map = request_maps(message, message_challenge)
global_map.append(global_map[1])
rejected(serialize((global_map, input_map, output_map)), INVALID_REQUEST)

rejected(serialize(request_maps(message, message_challenge), tail=b'\x00'), INVALID_REQUEST)
rejected(psbt[:-3], INVALID_REQUEST)
rejected(b'psbu' + psbt[4:], INVALID_REQUEST)

global_map, input_map, output_map = request_maps(message, message_challenge)
global_map[0] = (b'\xfb', pack('<I', 2))
rejected(serialize((global_map, input_map, output_map)), INVALID_REQUEST)

return_value.write(b'OK')
