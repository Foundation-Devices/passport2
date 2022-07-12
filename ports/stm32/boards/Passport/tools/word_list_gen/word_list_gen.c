// SPDX-FileCopyrightText: 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

uint32_t NUM_WORDS = 0;
#define MAX_WORD_LEN 8

extern const char* bip39_words[];
extern const char* bytewords_words[];

#include <assert.h>
#include <stdint.h>
#include <string.h>

typedef struct {
    uint32_t keypad_digits;
    uint16_t offsets;
    char     word[MAX_WORD_LEN + 1];
} word_info_t;

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

// Convert a seed word to its equivalent in keypad numbers - max will be 8 digits long
uint32_t word_to_keypad_numbers(char* word) {
    uint32_t result = 0;

    uint32_t len = strlen(word);

    for (uint32_t i = 0; i < len; i++) {
        char     letter = word[i];
        uint32_t n      = letter_to_number(letter);
        result          = result * 10 + n;
    }
    return result;
}

uint16_t word_to_bit_offsets(char* word) {
    uint16_t result = 0;

    uint32_t len   = strlen(word);
    uint16_t shift = 14;

    for (uint32_t i = 0; i < len; i++) {
        char     letter = word[i];
        uint16_t n      = letter_to_offset(letter);
        result          = (n << shift) | result;
        shift -= 2;
    }
    return result;
}

int compare_word_info(const void* a, const void* b) {
    word_info_t* wa = (word_info_t*)a;
    word_info_t* wb = (word_info_t*)b;

    return wa->keypad_digits - wb->keypad_digits;
}

void make_num_pairs_array(const char** words, char* prefix) {
    // Insert the hyphen all weird like this so that `reuse lint` doesn't complain about parsing this
    printf("// SPDX%cFileCopyrightText: 2021 Foundation Devices, Inc. <hello@foundationdevices.com>\n", '-');
    printf("// SPDX%cLicense-Identifier: GPL-3.0-or-later\n", '-');
    printf("//\n\n");
    printf("#include <stdint.h>\n\n");

    printf("typedef struct {\n");
    printf("  uint32_t keypad_digits;\n");
    printf("  uint16_t offsets;\n");
    printf("} word_info_t;\n\n");

    printf("word_info_t %s_word_info[] = {\n", prefix);

    // Allocate a parallel array
    word_info_t* output = malloc(sizeof(word_info_t) * NUM_WORDS);

    for (int i = 0; i < NUM_WORDS; i++) {
        output[i].keypad_digits = word_to_keypad_numbers((char*)words[i]);
        output[i].offsets       = word_to_bit_offsets((char*)words[i]);
        strcpy(output[i].word, words[i]);
    }

    // Sort the array
    qsort(output, NUM_WORDS, sizeof(word_info_t), compare_word_info);

    for (int i = 0; i < NUM_WORDS; i++) {
        printf("  {%u, 0x%04x}%s // %s\n", output[i].keypad_digits, output[i].offsets, i == NUM_WORDS - 1 ? "" : ",",
               output[i].word);
    }
    printf("};\n");
}

void printUsage() {
    printf("Usage: word_list_gen [bip39|bytewords]\n");
}

int main(int argc, char** argv) {
    const char** words = NULL;
    if (argc > 1) {
        if (strcmp(argv[1], "bip39") == 0) {
            words     = bip39_words;
            NUM_WORDS = 2048;
        } else if (strcmp(argv[1], "bytewords") == 0) {
            words     = bytewords_words;
            NUM_WORDS = 256;
        }
    }

    if (words == NULL) {
        printUsage();
        return -1;
    }

    make_num_pairs_array(words, argv[1]);
    return 0;
}
