# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# A developer firmware pubkey that is not a point on secp256k1 can never verify a
# signature, so it must not reach the secure element slot in the first place.

from taproot import bytes_from_int, p as FIELD_PRIME, scalar_multiply, x, y
from utils import is_valid_firmware_pubkey

# secp256k1 G, the generator.
GENERATOR_X = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
GENERATOR_Y = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8


def serialize(x_coord, y_coord):
    '''64 bytes of x then y, the form the secure element slot holds.'''

    return bytes_from_int(x_coord) + bytes_from_int(y_coord)


assert is_valid_firmware_pubkey(serialize(GENERATOR_X, GENERATOR_Y))

# The negation of a point is also on the curve.
assert is_valid_firmware_pubkey(serialize(GENERATOR_X, FIELD_PRIME - GENERATOR_Y))

# A few more real points, so this is not just one hardcoded pair.
for multiplier in (2, 3, 7, 0x1234567890abcdef):
    point = scalar_multiply(multiplier)
    assert is_valid_firmware_pubkey(serialize(x(point), y(point))), \
        'rejected {} * G'.format(multiplier)

# The all zero key is how an empty slot reads. Removing a key has its own flow, so
# this one must not accept it as something to install.
assert not is_valid_firmware_pubkey(bytes(64))

# y is off by one, so the point is not on the curve.
assert not is_valid_firmware_pubkey(serialize(GENERATOR_X, GENERATOR_Y + 1))
assert not is_valid_firmware_pubkey(serialize(GENERATOR_X, GENERATOR_Y - 1))

# x is off by one: some x values have no square root at all, and this one does not.
assert not is_valid_firmware_pubkey(serialize(GENERATOR_X + 1, GENERATOR_Y))

# A zero coordinate beside a real one is not a point either.
assert not is_valid_firmware_pubkey(serialize(GENERATOR_X, 0))
assert not is_valid_firmware_pubkey(serialize(0, GENERATOR_Y))

# Coordinates have to be reduced, so p itself is out of range on either side.
assert not is_valid_firmware_pubkey(bytes_from_int(FIELD_PRIME) + bytes_from_int(GENERATOR_Y))
assert not is_valid_firmware_pubkey(bytes_from_int(GENERATOR_X) + bytes_from_int(FIELD_PRIME))

# All ones is neither reduced nor on the curve.
assert not is_valid_firmware_pubkey(b'\xff' * 64)

# The length is fixed by the slot.
assert not is_valid_firmware_pubkey(b'')
assert not is_valid_firmware_pubkey(serialize(GENERATOR_X, GENERATOR_Y)[0:63])
assert not is_valid_firmware_pubkey(serialize(GENERATOR_X, GENERATOR_Y) + b'\x00')

# A bytearray, which is what read_user_firmware_pubkey() hands back.
assert is_valid_firmware_pubkey(bytearray(serialize(GENERATOR_X, GENERATOR_Y)))

return_value.write(b'OK')
