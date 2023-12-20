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
    from utils import get_width_from_num_words
    import common
    from trezorcrypto import bip39
    import uio

    binary_str = uio.StringIO()

    for word in word_list:
        index = bip39.find_word(word)
        index_bin = '{:011b}'.format(index)
        binary_str.write(index_bin)

    # Determine how much more entropy is needed
    total_bits = get_width_from_num_words(len(word_list) + 1) * 8
    entropy_needed = total_bits - len(binary_str.getvalue())

    extra_entropy = bytearray(1)
    common.noise.random_bytes(extra_entropy, common.noise.ALL)
    entropy_bin = '{:08b}'.format(extra_entropy[0])[:entropy_needed]
    print("len(word_list): {}, total_bits: {}, len(binary_str): {}".format(len(word_list),
                                                                           total_bits,
                                                                           len(binary_str.getvalue())))
    print("entropy_needed: {}, extra_entropy: {}, entropy_bin: {}".format(entropy_needed,
                                                                          extra_entropy[0],
                                                                          entropy_bin))

    binary_str.write(entropy_bin)

    binary_str = binary_str.getvalue()

    width = get_width_from_num_words(len(word_list) + 1)
    as_bytes = bytearray(width)
    for i in range(0, width):
        as_bytes[i] = int('0b' + binary_str[i * 8:(i + 1) * 8], 2)

    # TODO: get checksum bits
    return 'abandon'
