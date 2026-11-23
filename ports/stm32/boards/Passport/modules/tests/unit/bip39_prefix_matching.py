# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# The bounds accounting in get_words_matching_prefix() has to hold for any buffer
# size and any requested match count. The binding hands it a 160 byte buffer, so
# the longest string it can return is 159 characters.

from foundation import bip39

MATCHES_LEN = 160
MAX_RESULT_LEN = MATCHES_LEN - 1

# Longest BIP39 word, so the largest entry is MAX_WORD_LEN + 1 with its separator.
MAX_WORD_LEN = 8

KEYPAD_LETTERS = ('abc', 'def', 'ghi', 'jkl', 'mno', 'pqrs', 'tuv', 'wxyz')

LETTER_TO_DIGIT = {}
for _digit, _letters in enumerate(KEYPAD_LETTERS):
    for _letter in _letters:
        LETTER_TO_DIGIT[_letter] = str(_digit + 2)


def to_digits(word):
    return ''.join([LETTER_TO_DIGIT[letter] for letter in word])


def must_reject(call):
    try:
        call()
    except ValueError:
        return

    raise RuntimeError('expected ValueError')


def matching(prefix, max_matches, word_list='bip39'):
    '''Call the binding and check the invariants that hold for every result.'''

    result = bip39.get_words_matching_prefix(prefix, max_matches, word_list)

    assert len(result) <= MAX_RESULT_LEN, \
        'result is {} bytes, the buffer is {}'.format(len(result) + 1, MATCHES_LEN)

    if result == '':
        return []

    words = result.split(',')
    for word in words:
        assert word != '', 'empty entry in {}'.format(result)
        assert to_digits(word).startswith(prefix), \
            '{} does not match prefix {}'.format(word, prefix)
    return words


# Ordinary predictive entry is unaffected.
assert matching(to_digits('abandon'), 5) == ['abandon']
assert 'cat' in matching(to_digits('cat'), 10)
# Shorter words sort first, so an exact match leads the list it shares with longer ones.
assert matching(to_digits('zoo'), 10)[0] == 'zoo'

# A prefix no word can match yields an empty list.
assert matching('999999999', 10) == []

# A broad prefix has far more matches than fit, so the result is truncated.
for prefix in ('2', '7', '22'):
    truncated = matching(prefix, 2048)
    # Truncation happens at the end of the buffer rather than well before it: the
    # match that did not fit needs at most MAX_WORD_LEN + 1 bytes.
    assert len(truncated) >= 25, \
        'only {} matches for prefix {}'.format(len(truncated), prefix)
    assert MAX_RESULT_LEN - len(','.join(truncated)) <= MAX_WORD_LEN

# max_matches still caps the result, and zero now means zero rather than unlimited.
assert len(matching('2', 10)) == 10
assert len(matching('2', 1)) == 1
assert matching('2', 0) == []

# A negative count would otherwise wrap to an effectively unlimited unsigned one.
must_reject(lambda: bip39.get_words_matching_prefix('2', -1, 'bip39'))

# Bytewords share the implementation and the same buffer.
assert len(matching(to_digits('acid'), 10, word_list='bytewords')) >= 1
assert len(matching('2', 256, word_list='bytewords')) >= 25

# An unrecognised word list selects no table at all.
assert bip39.get_words_matching_prefix('2', 10, 'not-a-word-list') is None

return_value.write(b'OK')
