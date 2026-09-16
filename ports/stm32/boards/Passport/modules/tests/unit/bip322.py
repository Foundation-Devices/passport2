# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Test BIP-322 Taproot message signing.

from foundation import secp256k1
from ubinascii import a2b_base64
from ubinascii import unhexlify as a2b_hex

from bip322 import create_virtual_transactions, sign_taproot_simple, taproot_signature_hash
from serializations import hash256
from taproot import output_script


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

return_value.write(b'OK')
