# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Optional arguments to foundation.ur.new_derived_key must reach Rust as real
# NULLs. Rust takes use_info and origin as Option<&T>, which is null-pointer
# optimized, so a bogus non-null address is read as Some and dereferenced.

from foundation import ur


KEY_DATA = b'\x02' + bytes(range(32))
CHAIN_CODE = bytes(range(32))

coin_info = ur.CoinInfo(0, ur.NETWORK_MAINNET)
keypath = ur.Keypath(source_fingerprint=0x12345678, depth=3)


def must_reject(call):
    try:
        call()
    except ValueError:
        return

    raise RuntimeError('expected ValueError')


# The optionals have to be omitted rather than passed as None: the binding
# compares against MP_OBJ_NULL, and None is a wrong-typed argument to it.
assert ur.new_derived_key(KEY_DATA, chain_code=CHAIN_CODE) is not None
assert ur.new_derived_key(KEY_DATA, chain_code=CHAIN_CODE, use_info=coin_info) is not None
assert ur.new_derived_key(KEY_DATA, chain_code=CHAIN_CODE, origin=keypath) is not None
assert ur.new_derived_key(KEY_DATA, chain_code=CHAIN_CODE,
                          use_info=coin_info, origin=keypath) is not None

# chain_code is optional too, and already reached Rust as a real NULL.
assert ur.new_derived_key(KEY_DATA) is not None
assert ur.new_derived_key(KEY_DATA, use_info=coin_info, origin=keypath) is not None

# parent_fingerprint is independent of the two pointer arguments.
assert ur.new_derived_key(KEY_DATA, parent_fingerprint=0x89abcdef) is not None

# Wrong types are still rejected rather than being treated as absent.
must_reject(lambda: ur.new_derived_key(KEY_DATA, use_info=1))
must_reject(lambda: ur.new_derived_key(KEY_DATA, origin=1))
must_reject(lambda: ur.new_derived_key(KEY_DATA, use_info=None))
must_reject(lambda: ur.new_derived_key(KEY_DATA, origin=None))

# key_data length is still enforced.
must_reject(lambda: ur.new_derived_key(b'\x02' * 32))
must_reject(lambda: ur.new_derived_key(b'\x02' * 34))
must_reject(lambda: ur.new_derived_key(KEY_DATA, chain_code=bytes(31)))

return_value.write(b'OK')
