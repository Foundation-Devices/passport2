# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# unwrap_bytes() and unwrap_psbt() return views, not copies. Callers keep a view
# after the Value it came from is gone (the QR signing flow holds the PSBT
# across a gc.collect()), so the bytes behind it must stay intact until the
# next decode, which reuses the decoder's storage. Pin that against heap reuse
# for single-part and multi-part decodes, and for values built locally.

import gc

from data_codecs.ur2_codec import UR2Decoder
from foundation import ur

SINGLE = bytes([(i * 7 + 3) & 0xff for i in range(100)])
MULTI = bytes([(i * 13 + 5) & 0xff for i in range(600)])


def decode(value):
    ur.encoder_start(value, 535)
    decoder = UR2Decoder()
    parts = 0
    while not decoder.is_complete():
        assert parts < 64, 'UR did not decode'
        decoder.add_data(ur.encoder_next_part())
        parts += 1
    return decoder.decode(), parts


def build(make, payload):
    # Nothing else refers to this buffer once the function returns.
    return make(bytearray(payload))


def churn(size):
    # Blocks freed by the collection would be handed out again here.
    gc.collect()
    return [bytearray(bytes([0xa5]) * size) for _ in range(64)]


for payload, multipart in ((SINGLE, False), (MULTI, True)):
    for make, unwrap in ((ur.new_bytes, 'unwrap_bytes'), (ur.new_psbt, 'unwrap_psbt')):
        value, parts = decode(make(payload))
        assert (parts > 1) == multipart
        view = getattr(value, unwrap)()
        del value
        junk = churn(len(payload))
        assert view == payload
        del view, junk

        value = build(make, payload)
        junk = churn(len(payload))
        assert getattr(value, unwrap)() == payload
        del value, junk

return_value.write(b'OK')
