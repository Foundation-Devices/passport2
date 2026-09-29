# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Which sighash types are supported depends on how an input gets signed.
# SIGHASH_DEFAULT only exists for taproot; legacy and segwit v0 inputs can only do
# SIGHASH_ALL. Digests are checked against straight-line reimplementations of the
# legacy and BIP-341 preimages, and taproot signatures against a pure Python BIP-340
# verifier, so nothing here shares code with what it is checking.

from uio import BytesIO
from ustruct import pack

from exceptions import FatalPSBTIssue
from psbt import psbtInputProxy, psbtObject
from serializations import (COutPoint, CTxIn, CTxOut, SIGHASH_ALL, SIGHASH_DEFAULT,
                            ser_compact_size, ser_string, sha256)
from taproot import (bytes_from_int, int_from_bytes, output_script, scalar_multiply,
                     tagged_hash, taproot_sign_key, taproot_tweak_seckey,
                     tweak_internal_key, x)

# secp256k1, written out here rather than imported, so verification below does not
# lean on the same arithmetic the signer uses.
FIELD = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
ORDER = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
GENERATOR = (0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
             0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8)

SECKEY = bytes(range(1, 33))


def curve_add(p1, p2):
    if p1 is None:
        return p2
    if p2 is None:
        return p1
    if p1[0] == p2[0] and p1[1] != p2[1]:
        return None

    if p1 == p2:
        lam = (3 * p1[0] * p1[0] * pow(2 * p1[1], FIELD - 2, FIELD)) % FIELD
    else:
        lam = ((p2[1] - p1[1]) * pow(p2[0] - p1[0], FIELD - 2, FIELD)) % FIELD

    x3 = (lam * lam - p1[0] - p2[0]) % FIELD
    return (x3, (lam * (p1[0] - x3) - p1[1]) % FIELD)


def curve_mul(point, n):
    result = None
    for _ in range(256):
        if n & 1:
            result = curve_add(result, point)
        point = curve_add(point, point)
        n >>= 1
    return result


def curve_lift_x(x_only):
    key = int_from_bytes(x_only)
    if key >= FIELD:
        return None

    y_sq = (pow(key, 3, FIELD) + 7) % FIELD
    y = pow(y_sq, (FIELD + 1) // 4, FIELD)
    if pow(y, 2, FIELD) != y_sq:
        return None

    return (key, y if y % 2 == 0 else FIELD - y)


def bip340_verify(pubkey, msg, sig):
    '''Transcribed from the BIP-340 reference pseudocode.'''

    point = curve_lift_x(pubkey)
    if point is None:
        return False

    r = int_from_bytes(sig[0:32])
    s = int_from_bytes(sig[32:64])
    if r >= FIELD or s >= ORDER:
        return False

    e = int_from_bytes(tagged_hash('BIP0340/challenge', sig[0:32] + pubkey + msg)) % ORDER

    # R = s*G - e*P
    computed = curve_add(curve_mul(GENERATOR, s), curve_mul(point, ORDER - e))
    if computed is None or computed[1] % 2 != 0:
        return False

    return computed[0] == r


def must_raise(exc_type, call):
    try:
        call()
    except exc_type:
        return

    raise RuntimeError('expected {}'.format(exc_type.__name__))


def message_of(call):
    '''An assertion on the signing path has to carry a message, since sign_psbt_task
    reads args[0] to report it.'''

    try:
        call()
    except AssertionError as e:
        assert e.args, 'assertion has no message'
        return e.args[0]

    raise RuntimeError('expected AssertionError')


# ---------------------------------------------------------------- input validation

class FakeInputProxy:
    def __init__(self, sighash, taproot):
        self.witness_script = None
        self.redeem_script = None
        self.sighash = sighash
        self.subpaths = {}
        self.tap_subpaths = {b'\x02' * 32: None} if taproot else {}
        self.tap_key_sig = None
        self.part_sig = {}
        self.utxo = None
        self.fully_signed = None

    def parse_subpaths(self, my_xfp):
        pass


def validate(sighash=None, taproot=False):
    inp = FakeInputProxy(sighash, taproot)
    psbtInputProxy.validate(inp, 0, None, 0)
    return inp.sighash


# An absent type still defaults by input type.
assert validate() == SIGHASH_ALL
assert validate(taproot=True) == SIGHASH_DEFAULT

# Explicit SIGHASH_ALL is supported everywhere, including on taproot.
assert validate(sighash=SIGHASH_ALL) == SIGHASH_ALL
assert validate(sighash=SIGHASH_ALL, taproot=True) == SIGHASH_ALL

# SIGHASH_DEFAULT is taproot only: elsewhere zero is not a defined hash type.
assert validate(sighash=SIGHASH_DEFAULT, taproot=True) == SIGHASH_DEFAULT
must_raise(FatalPSBTIssue, lambda: validate(sighash=SIGHASH_DEFAULT))

for bad in (2, 3, 0x81, 0xffffffff):
    must_raise(FatalPSBTIssue, lambda: validate(sighash=bad))
    must_raise(FatalPSBTIssue, lambda: validate(sighash=bad, taproot=True))


# ------------------------------------------------------------------ the transaction

INTERNAL_PUBKEY = bytes_from_int(x(scalar_multiply(int_from_bytes(SECKEY))))
P2TR_SCRIPT = output_script(INTERNAL_PUBKEY, None)
P2WPKH_SCRIPT = b'\x00\x14' + (b'\x33' * 20)

SPEC = {
    'version': 2,
    'locktime': 500000,
    'inputs': [
        {'hash': 0xa1a1, 'n': 0, 'seq': 0xfffffffd, 'value': 120000, 'spk': P2TR_SCRIPT},
        {'hash': 0xb2b2, 'n': 3, 'seq': 0xffffffff, 'value': 90000, 'spk': P2TR_SCRIPT},
    ],
    'outputs': [
        {'value': 180000, 'spk': P2WPKH_SCRIPT},
        {'value': 25000, 'spk': P2TR_SCRIPT},
    ],
}


def ser_txn(spec):
    body = pack('<i', spec['version'])
    body += ser_compact_size(len(spec['inputs']))
    for i in spec['inputs']:
        body += CTxIn(COutPoint(i['hash'], i['n']), b'', i['seq']).serialize()
    body += ser_compact_size(len(spec['outputs']))
    for o in spec['outputs']:
        body += CTxOut(o['value'], o['spk']).serialize()
    body += pack('<I', spec['locktime'])
    return body


class FakeInput:
    def __init__(self, spec_input, segwit):
        self.spec = spec_input
        self.is_segwit = segwit
        self.witness_utxo = segwit

    def get_utxo(self, _n):
        return CTxOut(self.spec['value'], self.spec['spk'])


class FakePSBT:
    '''Just enough of a psbtObject for the sighash builders to run on.'''

    def __init__(self, spec, segwit):
        raw = ser_txn(spec)
        self.fd = BytesIO(raw)
        self.txn = (0, len(raw))
        self.total_value_out = None
        self.inputs = [FakeInput(i, segwit) for i in spec['inputs']]
        self.tap_hashPrevouts = None
        self.tap_hashSequence = None
        self.tap_hashOutputs = None
        self.hashAmounts = None
        self.hashScriptPubkeys = None
        psbtObject.parse_txn(self)

    # The sighash builders walk the transaction through these.
    def input_iter(self):
        return psbtObject.input_iter(self)

    def output_iter(self):
        return psbtObject.output_iter(self)


# ------------------------------------------------------------------ taproot digests

def ref_taproot_sighash(spec, input_idx, hash_type):
    '''BIP-341 SigMsg for a key path spend with no annex, built in one pass.'''

    prevouts = b''.join([COutPoint(i['hash'], i['n']).serialize() for i in spec['inputs']])
    amounts = b''.join([pack('<q', i['value']) for i in spec['inputs']])
    script_pubkeys = b''.join([ser_string(i['spk']) for i in spec['inputs']])
    sequences = b''.join([pack('<I', i['seq']) for i in spec['inputs']])
    outputs = b''.join([CTxOut(o['value'], o['spk']).serialize() for o in spec['outputs']])

    msg = bytes([hash_type])
    msg += pack('<i', spec['version'])
    msg += pack('<I', spec['locktime'])
    msg += sha256(prevouts)
    msg += sha256(amounts)
    msg += sha256(script_pubkeys)
    msg += sha256(sequences)
    msg += sha256(outputs)
    msg += b'\x00'                      # spend_type: key path, no annex
    msg += pack('<I', input_idx)

    return tagged_hash('TapSighash', b'\x00' + msg)


psbt = FakePSBT(SPEC, True)

digests = {}
for hash_type in (SIGHASH_DEFAULT, SIGHASH_ALL):
    for input_idx in (0, 1):
        digest = psbtObject.make_txn_taproot_sighash(psbt, input_idx, hash_type)
        assert digest == ref_taproot_sighash(SPEC, input_idx, hash_type), \
            'taproot digest mismatch for type {} input {}'.format(hash_type, input_idx)
        digests[(hash_type, input_idx)] = digest

# The hash type is committed to, so the two ALL modes are not interchangeable.
assert digests[(SIGHASH_DEFAULT, 0)] != digests[(SIGHASH_ALL, 0)]
assert digests[(SIGHASH_DEFAULT, 0)] != digests[(SIGHASH_DEFAULT, 1)]

# Unsupported types stop before any signing, with something to report.
message_of(lambda: psbtObject.make_txn_taproot_sighash(psbt, 0, 2))


# --------------------------------------------------------------- taproot signatures

TWEAKED_PUBKEY = tweak_internal_key(INTERNAL_PUBKEY, b'')[1]

# Key path signing uses the tweaked key, so the two must differ to begin with.
assert TWEAKED_PUBKEY != INTERNAL_PUBKEY
assert taproot_tweak_seckey(SECKEY, b'') != SECKEY

signatures = {}
for hash_type in (SIGHASH_DEFAULT, SIGHASH_ALL):
    digest = digests[(hash_type, 0)]
    sig = taproot_sign_key(None, SECKEY, hash_type, digest)
    signatures[hash_type] = sig

    # BIP-341: a 64 byte signature means SIGHASH_DEFAULT, anything else carries its
    # hash type as a 65th byte.
    if hash_type == SIGHASH_DEFAULT:
        assert len(sig) == 64
    else:
        assert len(sig) == 65
        assert sig[64] == hash_type

    assert bip340_verify(TWEAKED_PUBKEY, digest, sig[0:64]), \
        'signature does not verify for type {}'.format(hash_type)

# It is a signature over that digest, by the tweaked key, and nothing else.
sig = signatures[SIGHASH_DEFAULT][0:64]
assert not bip340_verify(INTERNAL_PUBKEY, digests[(SIGHASH_DEFAULT, 0)], sig)
assert not bip340_verify(TWEAKED_PUBKEY, digests[(SIGHASH_ALL, 0)], sig)


# -------------------------------------------------------------------- legacy digest

SCRIPT_SIG = b'\x76\xa9\x14' + (b'\x44' * 20) + b'\x88\xac'


def ref_legacy_sighash(spec, replace_idx, script_sig, hash_type):
    body = pack('<i', spec['version'])
    body += ser_compact_size(len(spec['inputs']))
    for idx, i in enumerate(spec['inputs']):
        sig_script = script_sig if idx == replace_idx else b''
        body += CTxIn(COutPoint(i['hash'], i['n']), sig_script, i['seq']).serialize()
    body += ser_compact_size(len(spec['outputs']))
    for o in spec['outputs']:
        body += CTxOut(o['value'], o['spk']).serialize()
    body += pack('<I', spec['locktime'])
    body += pack('<I', hash_type)

    return sha256(sha256(body))


legacy_psbt = FakePSBT(SPEC, False)

for replace_idx in (0, 1):
    spec_input = SPEC['inputs'][replace_idx]
    replacement = CTxIn(COutPoint(spec_input['hash'], spec_input['n']),
                        SCRIPT_SIG, spec_input['seq'])
    digest = psbtObject.make_txn_sighash(legacy_psbt, replace_idx, replacement, SIGHASH_ALL)
    assert digest == ref_legacy_sighash(SPEC, replace_idx, SCRIPT_SIG, SIGHASH_ALL)

# The preimage commits to the type that ser_sig_der() serializes beside the
# signature, so the two cannot disagree.
message_of(lambda: psbtObject.make_txn_sighash(legacy_psbt, 1, replacement, SIGHASH_DEFAULT))


# ----------------------------------------------------------------- segwit v0 digest

SCRIPT_CODE = b'\x19\x76\xa9\x14' + (b'\x55' * 20) + b'\x88\xac'

message_of(lambda: psbtObject.make_txn_segwit_sighash(psbt, 0, replacement, 120000,
                                                      SCRIPT_CODE, SIGHASH_DEFAULT))

return_value.write(b'OK')
