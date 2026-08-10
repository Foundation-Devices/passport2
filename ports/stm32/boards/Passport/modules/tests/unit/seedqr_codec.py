# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from data_codecs.seedqr_codec import SeedQRDecoder


def decode(data):
    decoder = SeedQRDecoder()
    decoder.add_data(data)
    return decoder.decode()


valid_12 = '0000' * 12
valid_24 = '2047' * 24

assert decode(valid_12) == ['abandon'] * 12
assert decode(valid_24) == ['zoo'] * 24

malformed = (
    '2048' + ('0000' * 11),
    '9999' + ('0000' * 11),
    'abcd' + ('0000' * 11),
    '-001' + ('0000' * 11),
    ' 001' + ('0000' * 11),
    valid_12 + '0',
    valid_12 + '000',
    valid_24 + '0',
)

for data in malformed:
    assert decode(data) is None

return_value.write(b'OK')
