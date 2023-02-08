# SPDX-FileCopyrightText: 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: BSD-2-Clause-Patent
#
# fountain_decoder.py
#

from .fountain_utils import choose_fragments, contains, is_strict_subset, set_difference
from .utils import join_lists, join_bytes, crc32_int, xor_with, take_first
from utils import bytes_to_hex_str


class FountainError(Exception):
    pass


class FountainDecoder:
    class Part:
        def __init__(self, indexes, data):
            self.indexes = frozenset(indexes)
            self.data = data

        @classmethod
        def from_encoder_part(cls, p):
            return cls(choose_fragments(p.seq_num, p.seq_len, p.checksum), p.data[:])

        def indexes(self):
            return self.indexes

        def data(self):
            return self.data

        def is_simple(self):
            return len(self.indexes) == 1

        def index(self):
            # TODO: Find a more efficient way of doing this (measure performance overhead first)
            return list(self.indexes)[0]

    # FountainDecoder
    def __init__(self):
        self.received_part_indexes = set()
        self.processed_parts_count = 0
        self.result = None
        self.expected_part_indexes = None
        self.expected_fragment_len = None
        self.expected_message_len = None
        self.expected_checksum = None
        self.simple_parts = {}
        self.mixed_parts = {}
        self.queued_parts = []

    def expected_part_count(self):
        if self.expected_part_indexes is None:
            return 0
        return len(self.expected_part_indexes)

    def is_complete(self):
        return self.result is not None

    def result(self):
        return self.result

    def estimated_percent_complete(self):
        if self.is_complete():
            return 1
        if self.expected_part_indexes is None:
            return 0
        estimated_input_parts = self.expected_part_count() * 1.75
        return min(0.99, self.processed_parts_count / estimated_input_parts)

    def receive_part(self, encoder_part):
        # Don't process the part if we're already done
        if self.is_complete():
            return False

        # Don't continue if this part doesn't validate
        if not self.validate_part(encoder_part):
            raise FountainError('Invalid part')

        # Add this part to the queue
        p = FountainDecoder.Part.from_encoder_part(encoder_part)
        self.enqueue(p)

        # Process the queue until we're done or the queue is empty
        while not self.is_complete() and len(self.queued_parts) != 0:
            self.process_queue_item()

        # Keep track of how many parts we've processed
        #
        # NOTE: We should only increment this if we haven't processed this part
        # before.
        if encoder_part.seq_num - 1 not in self.received_part_indexes:
            self.processed_parts_count += 1

        # self.print_part_end()

        return True

    # Join all the fragments of a message together, throwing away any padding
    @staticmethod
    def join_fragments(fragments, message_len):
        message = join_bytes(fragments)
        return take_first(message, message_len)

    def enqueue(self, p):
        self.queued_parts.append(p)

    def process_queue_item(self):
        part = self.queued_parts.pop(0)
        # self.print_part(part)

        if part.is_simple():
            self.process_simple_part(part)
        else:
            self.process_mixed_part(part)
        # self.print_state()

    def reduce_mixed_by(self, p):
        # Reduce all the current mixed parts by the given part
        reduced_parts = []
        for value in self.mixed_parts.values():
            reduced_parts.append(self.reduce_part_by_part(value, p))

        # Collect all the remaining mixed parts
        new_mixed = {}
        for reduced_part in reduced_parts:
            # If this reduced part is now simple
            if reduced_part.is_simple():
                # Add it to the queue
                self.enqueue(reduced_part)
            else:
                # Otherwise, add it to the dict of current mixed parts
                new_mixed[reduced_part.indexes] = reduced_part

        self.mixed_parts = new_mixed

    def reduce_part_by_part(self, a, b):
        # If the fragments mixed into `b` are a strict (proper) subset of those in `a`...
        if is_strict_subset(b.indexes, a.indexes):
            # The new fragments in the revised part are `a` - `b`.
            new_indexes = set_difference(a.indexes, b.indexes)
            # The new data in the revised part are `a` XOR `b`
            new_data = xor_with(bytearray(a.data), b.data)
            return self.Part(new_indexes, new_data)
        else:
            # `a` is not reducible by `b`, so return a
            return a

    def process_simple_part(self, p):
        # Don't process duplicate parts
        fragment_index = p.index()
        if contains(self.received_part_indexes, fragment_index):
            return

        # Record this part
        self.simple_parts[p.indexes] = p
        if fragment_index not in self.received_part_indexes:
            self.received_part_indexes.add(fragment_index)
            self.processed_parts_count += 1

        # If we've received all the parts
        if self.received_part_indexes == self.expected_part_indexes:
            # Reassemble the message from its fragments
            sorted_parts = []
            for value in self.simple_parts.values():
                sorted_parts.append(value)

            sorted_parts.sort(key=lambda a: a.index())

            fragments = []
            for part in sorted_parts:
                fragments.append(part.data)

            message = self.join_fragments(fragments, self.expected_message_len)

            # Verify the message checksum and note success or failure
            checksum = crc32_int(message)
            if checksum == self.expected_checksum:
                result = bytes(message)
                self.result = result
            else:
                raise FountainError('Invalid part checksum')
        else:
            # Reduce all the mixed parts by this part
            self.reduce_mixed_by(p)

    def process_mixed_part(self, p):
        # Don't process duplicate parts
        for r in self.mixed_parts.values():
            if r == p.indexes:
                return

        # Reduce this part by all the others
        p2 = p
        for r in self.simple_parts.values():
            p2 = self.reduce_part_by_part(p2, r)

        for r in self.mixed_parts.values():
            p2 = self.reduce_part_by_part(p2, r)

        # If the part is now simple
        if p2.is_simple():
            # Add it to the queue
            self.enqueue(p2)
        else:
            # Reduce all the mixed parts by this one
            self.reduce_mixed_by(p2)
            # Record this new mixed part
            self.mixed_parts[p2.indexes] = p2

    def validate_part(self, p):
        # If this is the first part we've seen
        if self.expected_part_indexes is None:
            # Record the things that all the other parts we see will have to match to be valid.
            self.expected_part_indexes = set()
            for i in range(p.seq_len):
                self.expected_part_indexes.add(i)

            self.expected_message_len = p.message_len
            self.expected_checksum = p.checksum
            self.expected_fragment_len = len(p.data)
        else:
            # If this part's values don't match the first part's values, throw away the part
            if self.expected_part_count() != p.seq_len:
                return False
            if self.expected_message_len != p.message_len:
                return False
            if self.expected_checksum != p.checksum:
                return False
            if self.expected_fragment_len != len(p.data):
                return False

        # This part should be processed
        return True

    # debugging
    def indexes_to_string(self, indexes):
        i = sorted(indexes)
        s = [str(j) for j in i]
        return '[{}]'.format(', '.join(s))

    # DEBUG CODE
    #
    # def result_description(self):
    #     if self.result is None:
    #         return 'None'
    #
    #     return '{} bytes'.format(len(self.result))
    #
    # def print_part(self, p):
    #     print('part indexes: {}'.format(self.indexes_to_string(p.indexes)))
    #
    # def print_part_end(self):
    #     expected = self.expected_part_count() if self.expected_part_indexes != None else 'None'
    #     percent = int(round(self.estimated_percent_complete() * 100))
    #     print("processed: {}, expected: {}, received: {}, percent: {}%".format(
    #         self.processed_parts_count, expected, len(self.received_part_indexes), percent))
    #
    # def print_state(self):
    #     parts = self.expected_part_count() if self.expected_part_indexes != None else 'None'
    #     received = self.indexes_to_string(self.received_part_indexes)
    #     mixed = []
    #     for indexes, p in self.mixed_parts.items():
    #         mixed.append(self.indexes_to_string(indexes))
    #
    #     mixed_s = "[{}]".format(', '.join(mixed))
    #     queued = len(self.queued_parts)
    #     res = self.result_description()
    #     print('parts: {}, received: {}, mixed: {}, queued: {}, result: {}'.format(
    #         parts, received, mixed_s, queued, res))
