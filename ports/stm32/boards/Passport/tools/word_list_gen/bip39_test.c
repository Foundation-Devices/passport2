// SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundation.xyz>
// SPDX-License-Identifier: GPL-3.0-or-later
//

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define NUM_WORDS 10
#define MAX_WORD_LEN 8

#include "../bip39_utils.h"

extern word_info_t word_info[];

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
void find_words_matching_prefix(char* prefix, char* matches, uint32_t matches_len, uint32_t max_matches) {
    char*    pnext_match = matches;
    char     candidate_keypad_digits[MAX_WORD_LEN + 1];
    uint32_t num_matches   = 0;
    uint32_t total_written = 0;

    for (uint32_t i = 0; i < NUM_WORDS; i++) {
        snprintf(candidate_keypad_digits, MAX_WORD_LEN + 1, "%d", word_info[i].keypad_digits);
        if (starts_with(candidate_keypad_digits, prefix)) {
            // This is a match, so convert the offsets to a real string and append to the buffer
            uint32_t len = word_info_to_string(candidate_keypad_digits, word_info[i].offsets, pnext_match);
            if (total_written + len > matches_len - 1) {
                // Don't write this one, as there is not enough room
                break;
            }
            total_written += len;

            pnext_match += len;
            *pnext_match = ',';
            pnext_match++;
            num_matches++;

            // Don't do more work than requested
            if (num_matches == max_matches) {
                break;
            }
        }
    }

    if (num_matches > 0) {
        // Overwrite the trailing comma
        pnext_match--;
    }
    *pnext_match = 0;

    printf("Returning matches: %s\n", matches);
}

int main(int argc, char* argv[]) {
    if (argc < 2) {
        printf("Usage: bip_test <prefix_digits>\n");
        printf("        e.g., 'bip_test 23'\n");
        return 0;
    }

    char matches[200];

    find_words_matching_prefix(argv[1], matches, 200, 7);

    return 0;
}
