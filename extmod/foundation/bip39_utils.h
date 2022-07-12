// SPDX-FileCopyrightText: 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//

#include <stdint.h>

// This structure stores the keypad digits required for a word (max 8 digits) in `keypad_digits`.
//
// The `offsets` field contains 8 sets of 2 bits each. Each 2-bit value is
// an offset from the corresponding keypad digit:
//
// Examples:
//
//   On the '2' key, offset of 'a' is 0, 'b' is 1 and 'c' is 2.
//   On the '7' key, offset of 'p' is 0, 'q' is 1 and 'r' is 2, and 's' is 3.
//
// If keypad_digits is '234', representing the word 'beg', then the offsets
// are 'b'=b01, 'e'=b01, 'g'=b00. The bits are encoded starting at the high end of the
// 16-bit value, so the final `offsets` value for '234' and 'beg' is b0101000000000000 or 0x5000.

typedef struct {
    uint32_t keypad_digits;
    uint16_t offsets;
} word_info_t;

void get_words_matching_prefix(char*              prefix,
                               char*              matches,
                               uint32_t           matches_len,
                               uint32_t           max_matches,
                               const word_info_t* word_info,
                               uint32_t           num_words);
