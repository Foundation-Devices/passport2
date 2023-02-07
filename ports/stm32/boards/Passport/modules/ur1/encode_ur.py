# SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
from .mini_cbor import encode_simple_cbor
from .bc32 import encode_bc32_data
from .utils import compose3
from ubinascii import hexlify


def compose_ur(payload, type='bytes'):
    return 'ur:{}/{}'.format(type, payload)


def compose_digest(payload, digest):
    return '{}/{}'.format(digest, payload)


def compose_sequencing(payload, index, total):
    return '{}of{}/{}'.format(index + 1, total, payload)


def compose_headers_to_fragments(fragments, digest, type='bytes'):
    if len(fragments) == 1:
        return [compose_ur(fragments[0])]

    result = []
    for index, f in enumerate(fragments):
        c = compose3(
            lambda payload: compose_ur(payload, type),
            lambda payload: compose_sequencing(payload, index, len(fragments)),
            lambda payload: compose_digest(payload, digest),
        )
        result.append(c(f))

    return result


def encode_ur(payload, fragment_capacity=1000):
    import foundation

    cbor_payload = encode_simple_cbor(payload)
    bc32_payload = encode_bc32_data(cbor_payload)
    digest = bytearray(32)
    foundation.sha256(cbor_payload, digest)
    bc32_digest = encode_bc32_data(digest)
    fragments = [bc32_payload[i:i + fragment_capacity] for i in range(0, len(bc32_payload), fragment_capacity)]
    if not fragments:
        raise ValueError('Unexpected error when encoding')

    return compose_headers_to_fragments(fragments, bc32_digest, 'bytes')
