# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# bip322.py - BIP-322 message-signing helpers

from ubinascii import b2a_base64
from ustruct import pack

from serializations import COutPoint, CTxIn, CTxOut
from serializations import SIGHASH_DEFAULT, hash256, ser_compact_size, ser_string, ser_string_vector, sha256
from taproot import output_script, tagged_hash, taproot_sign_key


BIP322_SIMPLE_PREFIX = 'smp'


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


def taproot_signature_hash(message, message_challenge):
    """Calculate the BIP-341 key-path sighash for a BIP-322 virtual spend."""
    to_spend, _ = create_virtual_transactions(message, message_challenge)

    outpoint = hash256(to_spend) + pack('<I', 0)
    to_sign_output = CTxOut(0, b'\x6a')

    # BIP-341 SigMsg: hash type, transaction fields, and aggregate input/output hashes.
    sigmsg = bytes([SIGHASH_DEFAULT])
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
    sighash = taproot_signature_hash(message, message_challenge)
    signature = taproot_sign_key(None, internal_seckey, SIGHASH_DEFAULT, sighash)
    witness = ser_string_vector([signature])

    encoded_witness = b2a_base64(witness).decode('ascii').strip()
    return BIP322_SIMPLE_PREFIX + encoded_witness
