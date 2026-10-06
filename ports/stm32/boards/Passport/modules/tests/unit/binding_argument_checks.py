# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# The foundation bindings validate their arguments with explicit raises. This
# pins each one: the error type for an invalid argument, and the valid call
# beside it so the checks cannot pass by refusing everything. See SFT-8229.

from data_codecs.ur2_codec import UR2Decoder
from foundation import bip39, ur

CONFIG = b'Name: Test wallet\n'


def must_raise(exc_type, call, what):
    try:
        call()
    except exc_type:
        return
    except BaseException as other:
        raise RuntimeError('{}: expected {}, got {}'.format(
            what, exc_type.__name__, type(other).__name__))

    raise RuntimeError('{}: expected {}, nothing raised'.format(what, exc_type.__name__))


# Each unwrap accepts only its own variant.
bytes_ur = ur.new_bytes(CONFIG)
psbt_ur = ur.new_psbt(CONFIG)

must_raise(ValueError, lambda: psbt_ur.unwrap_bytes(), 'unwrap_bytes on a psbt UR')
must_raise(ValueError, lambda: bytes_ur.unwrap_psbt(), 'unwrap_psbt on a bytes UR')
must_raise(ValueError, lambda: bytes_ur.unwrap_passport_request(),
           'unwrap_passport_request on a bytes UR')

# The matching variant still works, so the checks are not simply refusing.
assert bytes_ur.unwrap_bytes() == CONFIG
assert psbt_ur.unwrap_psbt() == CONFIG

# A crypto-request with only a UUID and a model has no SCV challenge, so the
# challenge accessors have nothing to return.
request_cbor = b'\xa2\x01\xd8\x25\x50' + bytes(16) + b'\x03\xd9\x02\xd0\xf5'
ur.encoder_start(ur.new_raw('crypto-request', request_cbor), 535)
decoder = UR2Decoder()
decoder.add_data(ur.encoder_next_part())
assert decoder.is_complete()
request = decoder.decode().unwrap_passport_request()

must_raise(ValueError, lambda: request.scv_challenge_id(), 'scv_challenge_id without a challenge')
must_raise(ValueError, lambda: request.scv_challenge_signature(),
           'scv_challenge_signature without a challenge')

# These three require a string argument.
for name, call in (
        ('ur.validate', lambda: ur.validate(123)),
        ('ur.decode_single_part', lambda: ur.decode_single_part(123)),
        ('ur.decoder_receive', lambda: ur.decoder_receive(123))):
    must_raise(TypeError, call, name)

# Same again in the bip39 bindings.
must_raise(TypeError, lambda: bip39.get_words_matching_prefix(123, 5, 'bip39'),
           'get_words_matching_prefix with a non-string prefix')
must_raise(TypeError, lambda: bip39.get_words_matching_prefix('2', 5, 123),
           'get_words_matching_prefix with a non-string word list')
must_raise(TypeError, lambda: bip39.mnemonic_to_bits(123, bytearray(33)),
           'mnemonic_to_bits with a non-string mnemonic')

# And the valid calls beside them are unaffected.
assert len(bip39.get_words_matching_prefix('2226366', 5, 'bip39')) > 0

return_value.write(b'OK')
