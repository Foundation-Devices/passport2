# SPDX-FileCopyrightText: 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
from .mini_cbor import decode_simple_cbor
from .bc32 import decode_bc32_data
from ubinascii import unhexlify as a2b_hex, hexlify as b2a_hex


def check_and_get_sequence(sequence):
    pieces = sequence.upper().split('OF')
    if len(pieces) != 2:
        raise ValueError('Invalid sequence definition')

    (index, total) = pieces
    return (int(index), int(total))


def check_digest(digest, payload):
    import foundation

    decoded = decode_bc32_data(payload)
    if decoded is None:
        raise ValueError('Unable to decode payload: {}'.format(payload))

    decoded_bytes = a2b_hex(decoded)
    sha = bytearray(32)
    foundation.sha256(decoded_bytes, sha)
    decoded_digest = b2a_hex(sha).decode()  # bytearray
    comp_digest = decode_bc32_data(digest)
    if comp_digest != decoded_digest:
        raise ValueError('Invalid digest:\n  digest={}\n  payload={}\nssSspayload digest={}'.format(
            digest, payload, decoded_digest))


def check_ur_header(ur, type='bytes'):
    if ur.upper() != 'ur:{}'.format(type).upper():
        raise ValueError('Invalid UR header: {}'.format(ur))


def deal_with_single_workload(workload, type='bytes'):
    pieces = workload.split('/')
    num_pieces = len(pieces)

    if num_pieces == 2:
        check_ur_header(pieces[0], type)
        return pieces[1]
    elif num_pieces == 3:
        check_ur_header(pieces[0], type)
        digest = pieces[1]
        fragment = pieces[2]
        check_digest(digest, fragment)
        return fragment
    elif num_pieces == 4:
        check_ur_header(pieces[0], type)
        check_and_get_sequence(pieces[1])
        digest = pieces[2]
        fragment = pieces[3]
        check_digest(digest, fragment)
        return fragment
    else:
        raise ValueError('Invalid workload pieces length: expected 2, 3 or 4, but got {}'.format(num_pieces))


def deal_with_multiple_workloads(workloads, type='bytes'):
    num_workloads = len(workloads)
    fragments = ['' for i in range(num_workloads)]
    digest = None
    for workload in workloads:
        # print('workload = {}'.format(workload))
        pieces = workload.split('/')
        # print('pieces = {}'.format(pieces))
        check_ur_header(pieces[0], type)
        (index, total) = check_and_get_sequence(pieces[1])
        if total != num_workloads:
            raise ValueError('Invalid workload length')

        if digest is not None and digest != pieces[2]:
            raise ValueError('Invalid workload digest mismatch')

        digest = pieces[2]
        if fragments[index - 1] != '':
            raise ValueError('Invalid workload: fragment at index {} has already been set'.format(index))

        fragments[index - 1] = pieces[3]

    payload = ''.join(fragments)

    check_digest(digest, payload)
    return payload


def get_bc32_payload(workloads, type='bytes'):
    try:
        num_workloads = len(workloads)
        if num_workloads == 1:
            return deal_with_single_workload(workloads[0], type)
        else:
            return deal_with_multiple_workloads(workloads, type)
    except Exception as e:
        raise ValueError('Invalid workloads: {}'.format(e))


def decode_ur(workloads, type='bytes'):
    bc32_payload = get_bc32_payload(workloads, type)
    cbor_payload = decode_bc32_data(bc32_payload)
    if cbor_payload is None:
        raise ValueError('Invalid CBOR data')

    result = decode_simple_cbor(cbor_payload)
    return result


def extract_single_workload(workload):
    pieces = workload.upper().split('/')
    num_pieces = len(pieces)

    if num_pieces == 2 or num_pieces == 3:
        return (1, 1)
    elif num_pieces == 4:
        return check_and_get_sequence(pieces[1])
    else:
        raise ValueError('Invalid workload pieces length: expected 2, 3, or 4, but got {}'.format(num_pieces))


class Workloads:
    def __init__(self):
        self.num_workloads = None
        self.workloads = None

    def add(self, workload):
        (index, total) = extract_single_workload(workload)

        # Convert from 0 to 1 based index
        index -= 1

        if self.workloads is None:
            self.num_workloads = total
            self.workloads = [None] * self.num_workloads
        elif self.num_workloads != total:
            raise ValueError('Workload total changed from {} to {}!'.format(self.num_workloads, total))

        if index < 0 or index >= self.num_workloads:
            raise ValueError('Workload index {} is out of range: [0, {})'.format(index, self.num_workloads))

        if self.workloads[index] is not None and self.workloads[index] != workload:
            raise ValueError('Received a second workload for index {} that is different than the first one:\n  old: {}\n  new: {}'.format(  # nopep8
                index, self.workloads[index], workload))

        # We have to make a copy of the workload string here because it's actually a buffer coming from the
        # modfoundation C code and it gets reused, so the contents changes out from under us if we don't
        # make a copy!
        self.workloads[index] = '{}'.format(workload)

    def is_complete(self):
        for w in range(self.num_workloads):
            if self.workloads[w] is None:
                return False

        return True

    def get_progress(self):
        num_parts = 0
        for w in range(self.num_workloads):
            if self.workloads[w] is not None:
                num_parts += 1

        return (num_parts, self.num_workloads)
