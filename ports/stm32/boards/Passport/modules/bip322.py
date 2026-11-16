# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# bip322.py - BIP-322 message-signing helpers

from ubinascii import b2a_base64
from uio import BytesIO
from ustruct import pack, unpack, unpack_from

from public_constants import MAX_PATH_DEPTH, PSBT_GLOBAL_GENERIC_SIGNED_MESSAGE, PSBT_GLOBAL_UNSIGNED_TX
from public_constants import PSBT_IN_SIGHASH_TYPE, PSBT_IN_TAP_BIP32_DERIVATION, PSBT_IN_TAP_KEY_SIG
from public_constants import PSBT_IN_WITNESS_UTXO
from serializations import COutPoint, CTxIn, CTxOut
from serializations import SIGHASH_ALL, SIGHASH_DEFAULT, deser_compact_size, hash256, ser_compact_size
from serializations import ser_string, ser_string_vector, sha256
from taproot import output_script, tagged_hash, taproot_sign_key


BIP322_SIMPLE_PREFIX = 'smp'

PSBT_MAGIC = b'psbt\xff'
INVALID_REQUEST = 'This is not a valid BIP-322 message request.'
TAPROOT_ONLY = 'Passport can only sign BIP-322 message requests for Taproot addresses. ' \
               'For other addresses, choose the Electrum format in your wallet.'


def _serialize_virtual_transaction(txin, txout):
    return pack('<i', 0) + \
        ser_compact_size(1) + txin.serialize() + \
        ser_compact_size(1) + txout.serialize() + \
        pack('<I', 0)


def create_virtual_transactions(message, message_challenge):
    """Create the BIP-322 to_spend and unsigned to_sign transactions."""
    message_hash = tagged_hash('BIP0322-signed-message', message)

    to_spend_input = CTxIn(
        COutPoint(0, 0xFFFFFFFF),
        b'\x00\x20' + message_hash,
        0,
    )
    to_spend_output = CTxOut(0, message_challenge)
    to_spend = _serialize_virtual_transaction(to_spend_input, to_spend_output)

    to_spend_hash = int.from_bytes(hash256(to_spend), 'little')
    to_sign_input = CTxIn(COutPoint(to_spend_hash, 0), b'', 0)
    to_sign_output = CTxOut(0, b'\x6a')
    to_sign = _serialize_virtual_transaction(to_sign_input, to_sign_output)

    return to_spend, to_sign


def taproot_signature_hash(message, message_challenge, hash_type=SIGHASH_DEFAULT):
    """Calculate the BIP-341 key-path sighash for a BIP-322 virtual spend."""
    to_spend, _ = create_virtual_transactions(message, message_challenge)

    outpoint = hash256(to_spend) + pack('<I', 0)
    to_sign_output = CTxOut(0, b'\x6a')

    # BIP-341 SigMsg: hash type, transaction fields, and aggregate input/output hashes.
    # SIGHASH_DEFAULT and SIGHASH_ALL commit to the same fields and differ only in this byte.
    sigmsg = bytes([hash_type])
    sigmsg += pack('<i', 0)
    sigmsg += pack('<I', 0)
    sigmsg += sha256(outpoint)
    sigmsg += sha256(pack('<q', 0))
    sigmsg += sha256(ser_string(message_challenge))
    sigmsg += sha256(pack('<I', 0))
    sigmsg += sha256(to_sign_output.serialize())

    # Key-path spend without an annex, followed by the input index.
    sigmsg += b'\x00'
    sigmsg += pack('<I', 0)

    return tagged_hash('TapSighash', b'\x00' + sigmsg)


def sign_taproot_simple(message, internal_pubkey, internal_seckey):
    """Create a textual BIP-322 simple signature for a P2TR key-path spend."""
    message_challenge = output_script(internal_pubkey, None)
    # BIP-322 lets P2TR use SIGHASH_DEFAULT, but every verifier has to accept SIGHASH_ALL, and Sparrow only
    # accepts SIGHASH_ALL.
    sighash = taproot_signature_hash(message, message_challenge, SIGHASH_ALL)
    signature = taproot_sign_key(None, internal_seckey, SIGHASH_ALL, sighash)
    witness = ser_string_vector([signature])

    encoded_witness = b2a_base64(witness).decode('ascii').strip()
    return BIP322_SIMPLE_PREFIX + encoded_witness


class SigningRequest:
    """A BIP-322 message-signing request sent as a PSBT, as Sparrow builds it."""

    def __init__(self, psbt, message, script_pubkey, xfp, path, hash_type, signature_offset):
        self.psbt = psbt
        self.message = message
        self.script_pubkey = script_pubkey
        self.xfp = xfp
        self.path = path
        self.hash_type = hash_type
        # Where the input's signature goes: just before the input map's terminator.
        self.signature_offset = signature_offset


def _read_exact(fd, length):
    data = fd.read(length)
    if len(data) != length:
        raise ValueError(INVALID_REQUEST)
    return data


def _read_map(fd):
    # Read one PSBT key-value map. BIP-174 forbids duplicate keys.
    entries = {}
    while True:
        key = _read_exact(fd, deser_compact_size(fd))
        if not key:
            return entries
        if key in entries:
            raise ValueError(INVALID_REQUEST)
        entries[key] = _read_exact(fd, deser_compact_size(fd))


def read_signing_request(psbt):
    """Read a BIP-322 message-signing request sent as a PSBT.

    The request is only accepted if its transaction is exactly the BIP-322 to_sign transaction for its own
    message and address, so the message shown for review is the one the signature commits to.
    """
    try:
        fd = BytesIO(psbt)
        if fd.read(len(PSBT_MAGIC)) != PSBT_MAGIC:
            raise ValueError(INVALID_REQUEST)

        global_map = _read_map(fd)
        input_map = _read_map(fd)
        signature_offset = fd.seek(0, 1) - 1       # .tell() is missing
        _read_map(fd)

        # One input and one output, and nothing after them.
        if fd.read(1):
            raise ValueError(INVALID_REQUEST)
    except Exception:
        raise ValueError(INVALID_REQUEST)

    unsigned_tx = global_map.get(bytes([PSBT_GLOBAL_UNSIGNED_TX]))
    message = global_map.get(bytes([PSBT_GLOBAL_GENERIC_SIGNED_MESSAGE]))
    witness_utxo = input_map.get(bytes([PSBT_IN_WITNESS_UTXO]))
    if unsigned_tx is None or witness_utxo is None:
        raise ValueError(INVALID_REQUEST)
    if message is None:
        raise ValueError('This request does not include the message to sign.')

    # The output being "spent" holds no value and pays to the address that signs.
    script_pubkey = witness_utxo[9:]
    if witness_utxo != pack('<q', 0) + ser_string(script_pubkey):
        raise ValueError(INVALID_REQUEST)
    if len(script_pubkey) != 34 or script_pubkey[:2] != b'\x51\x20':
        raise ValueError(TAPROOT_ONLY)

    _, to_sign = create_virtual_transactions(message, script_pubkey)
    if unsigned_tx != to_sign:
        raise ValueError('The transaction in this request does not match its message.')

    if bytes([PSBT_IN_TAP_KEY_SIG]) in input_map:
        raise ValueError('This message request is already signed.')

    hash_type = input_map.get(bytes([PSBT_IN_SIGHASH_TYPE]))
    if hash_type is None:
        hash_type = SIGHASH_DEFAULT
    elif len(hash_type) == 4:
        hash_type = unpack('<I', hash_type)[0]
    if hash_type not in (SIGHASH_DEFAULT, SIGHASH_ALL):
        raise ValueError('Unsupported signature hash type.')

    # Exactly one key-path derivation (no leaf hashes): the master fingerprint, then at least one step.
    derivations = [value for key, value in input_map.items()
                   if key[0] == PSBT_IN_TAP_BIP32_DERIVATION and len(key) == 33]
    if len(derivations) != 1:
        raise ValueError(INVALID_REQUEST)
    derivation = derivations[0]
    count = (len(derivation) - 1) // 4
    if derivation[0] != 0 or (len(derivation) - 1) % 4 or not 2 <= count <= MAX_PATH_DEPTH:
        raise ValueError(INVALID_REQUEST)
    xfp_path = list(unpack_from('<%dI' % count, derivation, 1))

    return SigningRequest(psbt, message, script_pubkey, xfp_path[0], xfp_path[1:], hash_type, signature_offset)


def sign_taproot_request(request, internal_pubkey, internal_seckey):
    """Sign a BIP-322 request and return its PSBT with the key-path signature added to the input."""
    if output_script(internal_pubkey, None) != request.script_pubkey:
        raise ValueError('The key does not match the address in the request.')

    sighash = taproot_signature_hash(request.message, request.script_pubkey, request.hash_type)
    signature = taproot_sign_key(None, internal_seckey, request.hash_type, sighash)

    psbt = request.psbt
    offset = request.signature_offset
    return psbt[:offset] + ser_compact_size(1) + bytes([PSBT_IN_TAP_KEY_SIG]) + ser_string(signature) + \
        psbt[offset:]
