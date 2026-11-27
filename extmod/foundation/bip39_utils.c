// SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundation.xyz>
// SPDX-License-Identifier: GPL-3.0-or-later
//

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>

#define NUM_WORDS 2048
#define MAX_WORD_LEN 8

#include "bip39_utils.h"

extern word_info_t bip39_word_info[];

#ifdef UNUSED_CODE
uint32_t letter_to_number(char ch) {
    if (ch >= 'a' && ch <= 'c') return 2;
    if (ch >= 'd' && ch <= 'f') return 3;
    if (ch >= 'g' && ch <= 'i') return 4;
    if (ch >= 'j' && ch <= 'l') return 5;
    if (ch >= 'm' && ch <= 'o') return 6;
    if (ch >= 'p' && ch <= 's') return 7;
    if (ch >= 't' && ch <= 'v') return 8;
    if (ch >= 'w' && ch <= 'z') return 9;
    assert(0);
    return 999;
}

uint32_t letter_to_offset(char ch) {
    if (ch >= 'a' && ch <= 'c') return ch - 'a';
    if (ch >= 'd' && ch <= 'f') return ch - 'd';
    if (ch >= 'g' && ch <= 'i') return ch - 'g';
    if (ch >= 'j' && ch <= 'l') return ch - 'j';
    if (ch >= 'm' && ch <= 'o') return ch - 'm';
    if (ch >= 'p' && ch <= 's') return ch - 'p';
    if (ch >= 't' && ch <= 'v') return ch - 't';
    if (ch >= 'w' && ch <= 'z') return ch - 'w';
    assert(0);
    return 999;
}
#endif

char key_and_offset_to_letter(char key, uint8_t offset) {
    switch (key) {
        case '2':
            return 'a' + offset;
        case '3':
            return 'd' + offset;
        case '4':
            return 'g' + offset;
        case '5':
            return 'j' + offset;
        case '6':
            return 'm' + offset;
        case '7':
            return 'p' + offset;
        case '8':
            return 't' + offset;
        case '9':
            return 'w' + offset;
        default:
            return 'X';
    }
}

// Assumes that word_buf is large enough (ensured by caller)
uint32_t word_info_to_string(char* keypad_digits, uint16_t offsets, char* word_buf) {
    uint32_t len = strlen(keypad_digits);

    for (uint32_t i = 0; i < len; i++) {
        uint8_t offset = (offsets >> (14 - i * 2)) & 0x3;
        char    letter = key_and_offset_to_letter(keypad_digits[i], offset);
        *word_buf      = letter;
        word_buf++;
    }
    return len;
}

uint8_t starts_with(const char* s, const char* prefix) {
    if (strncmp(s, prefix, strlen(prefix)) == 0) {
        return 1;
    }
    return 0;
}

// Fills in `matches` with a comma-separated list of matching words
void get_words_matching_prefix(char*              prefix,
                               char*              matches,
                               uint32_t           matches_len,
                               uint32_t           max_matches,
                               const word_info_t* word_info,
                               uint32_t           num_words) {
    char*    pnext_match = matches;
    char     candidate_keypad_digits[MAX_WORD_LEN + 1];
    uint32_t num_matches   = 0;
    uint32_t total_written = 0;

    if (matches_len == 0) {
        // Not even room for the terminator
        return;
    }

    // Don't do more work than requested
    for (uint32_t i = 0; i < num_words && num_matches < max_matches; i++) {
        snprintf(candidate_keypad_digits, MAX_WORD_LEN + 1, "%"PRIu32, word_info[i].keypad_digits);
        if (starts_with(candidate_keypad_digits, prefix)) {
            uint32_t len = strlen(candidate_keypad_digits);

            // Room for the word plus the separator that follows it, which the terminator
            // later overwrites, so this accounts for the terminator too
            if (total_written + len + 1 > matches_len) {
                // Don't write this one, as there is not enough room
                break;
            }

            // This is a match, so convert the offsets to a real string and append to the buffer
            word_info_to_string(candidate_keypad_digits, word_info[i].offsets, pnext_match);
            total_written += len + 1;

            pnext_match += len;
            *pnext_match = ',';
            pnext_match++;
            num_matches++;
        }
    }

    if (num_matches > 0) {
        // Overwrite the trailing comma
        pnext_match--;
    }
    *pnext_match = 0;
}
