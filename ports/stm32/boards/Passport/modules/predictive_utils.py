# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# predictive_utils.py - Utility functions for working with BIP39 seed phrases and bytewords.
#

# Map from keypad letters to keypad numbers
letter_to_number = {
    'a': 2,
    'b': 2,
    'c': 2,
    'd': 3,
    'e': 3,
    'f': 3,
    'g': 4,
    'h': 4,
    'i': 4,
    'j': 5,
    'k': 5,
    'l': 5,
    'm': 6,
    'n': 6,
    'o': 6,
    'p': 7,
    'q': 7,
    'r': 7,
    's': 7,
    't': 8,
    'u': 8,
    'v': 8,
    'w': 9,
    'x': 9,
    'y': 9,
    'z': 9,
}


def word_to_keypad_numbers(word):
    '''
    Convert a seed word to its equivalent in keypad numbers
    '''
    result = 0
    for letter in word:
        n = letter_to_number[letter]
        result = result * 10 + n
    return result


def get_words_matching_prefix(prefix, max=5, word_list='bip39'):
    from foundation import bip39

    # This actually handles bytewords too, depsite the name :(
    matches = bip39.get_words_matching_prefix(prefix, max, word_list)
    words = matches.split(',')

    # Python split() is brain-damaged - returns an array with a single empty string
    # in the case where you split an empty string.
    if len(words) == 1 and words[0] == '':
        words = []
    return words


def get_last_word(seed_words, word_list='bip39'):
    import trezorcrypto
    import common
    from foundation import bip39
    from utils import get_seed_from_words, get_words_from_seed
    from public_constants import SEED_WORD_LIST_LENGTH

    # The last word is partially entropy, partially checksum,
    # in different proportions based on the mnemonic length,

    # choose a random last word
    index_bytes = bytearray(2)  # 16 bit int
    common.noise.random_bytes(index_bytes, common.noise.ALL)
    index = int.from_bytes(index_bytes, "little") % SEED_WORD_LIST_LENGTH
    mock_last_word = trezorcrypto.bip39.get_word(index)
    copy_words = ' '.join(seed_words)  # Later function requires joined string
    copy_words += ' ' + mock_last_word

    # compute the bits without the checksum
    entropy = get_seed_from_words(copy_words)

    # get the correct words with the checkusm
    (final_words, error) = get_words_from_seed(entropy)

    if not final_words:
        return ""

    # return the correct final word
    return final_words[-1]
