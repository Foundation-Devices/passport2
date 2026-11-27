# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Buffer length validation in the trezorcrypto.ecdsa bindings. bn_read_be()
# always reads 32 bytes, so a shorter buffer would read past its end.

from trezorcrypto import ecdsa
from ubinascii import unhexlify as a2b_hex


GENERATOR_X = a2b_hex('79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798')
GENERATOR_Y = a2b_hex('483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8')

BAD_LENGTHS = (
    b'',
    b'\x01',
    b'\x01' * 31,
    b'\x01' * 33,
    b'\x01' * 64,
)


def scalar(value):
    return bytes(31) + bytes([value])


def must_reject(call):
    try:
        call()
    except ValueError:
        return

    raise RuntimeError('expected ValueError')


# Valid operations still work: 1 * G is the generator.
x1, y1 = ecdsa.scalar_multiply(scalar(1))
assert x1 == GENERATOR_X
assert y1 == GENERATOR_Y

# G + 2G == 3G, checked against scalar_multiply so the vector does not depend on
# a hardcoded point. The two addends differ, so this is not the doubling case.
x2, y2 = ecdsa.scalar_multiply(scalar(2))
x3, y3 = ecdsa.scalar_multiply(scalar(3))
assert ecdsa.point_add(x1, y1, x2, y2) == (x3, y3)

# Every scalar length other than 32 is rejected.
for bad in BAD_LENGTHS:
    must_reject(lambda: ecdsa.scalar_multiply(bad))

# ...and every coordinate of point_add, in each position.
for bad in BAD_LENGTHS:
    must_reject(lambda: ecdsa.point_add(bad, y1, x2, y2))
    must_reject(lambda: ecdsa.point_add(x1, bad, x2, y2))
    must_reject(lambda: ecdsa.point_add(x1, y1, bad, y2))
    must_reject(lambda: ecdsa.point_add(x1, y1, x2, bad))

# A rejected call must not have disturbed the valid path.
assert ecdsa.point_add(x1, y1, x2, y2) == (x3, y3)

return_value.write(b'OK')
