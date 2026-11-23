# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Error codes are built from a tuple of names, so a missing comma silently
# concatenates two of them into one member. The intended names then don't
# exist, and every reference to them raises AttributeError at runtime.

from errors import Error


for name in ('MULTISIG_STORAGE_IDX_ERROR', 'NOT_BIP39_MODE'):
    assert hasattr(Error, name), name

assert Error.MULTISIG_STORAGE_IDX_ERROR != Error.NOT_BIP39_MODE

# The exact symptom of the missing comma this test was added for.
assert not hasattr(Error, 'MULTISIG_STORAGE_IDX_ERRORNOT_BIP39_MODE')

return_value.write(b'OK')
