/**
 * Copyright (c) 2013-2014 Tomas Dzetkulic
 * Copyright (c) 2013-2014 Pavol Rusnak
 *
 * Permission is hereby granted, free of charge, to any person obtaining
 * a copy of this software and associated documentation files (the "Software"),
 * to deal in the Software without restriction, including without limitation
 * the rights to use, copy, modify, merge, publish, distribute, sublicense,
 * and/or sell copies of the Software, and to permit persons to whom the
 * Software is furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included
 * in all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
 * OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
 * THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES
 * OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
 * ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 * OTHER DEALINGS IN THE SOFTWARE.
 */

#include <stdbool.h>
#include <string.h>

#include "bip39.h"
#include "bip39_english.h"
#include "hmac.h"
#include "memzero.h"
#include "options.h"
#include "pbkdf2.h"
#include "rand.h"
#include "sha2.h"

#if USE_BIP39_CACHE

static int bip39_cache_index = 0;

static CONFIDENTIAL struct {
  bool set;
  char mnemonic[256];
  char passphrase[64];
  uint8_t seed[512 / 8];
} bip39_cache[BIP39_CACHE_SIZE];

#endif

const char *mnemonic_generate(int strength) {
  if (strength % 32 || strength < 128 || strength > 256) {
    return 0;
  }
  uint8_t data[32] = {0};
  random_buffer(data, 32);
  const char *r = mnemonic_from_data(data, strength / 8);
  memzero(data, sizeof(data));
  return r;
}

static CONFIDENTIAL char mnemo[24 * 10];

const char *mnemonic_from_data(const uint8_t *data, int len) {
  if (len % 4 || len < 16 || len > 32) {
    return 0;
  }

  uint8_t bits[32 + 1] = {0};

  sha256_Raw(data, len, bits);
  // checksum
  bits[len] = bits[0];
  // data
  memcpy(bits, data, len);

  int mlen = len * 3 / 4;

  int i = 0, j = 0, idx = 0;
  char *p = mnemo;
  for (i = 0; i < mlen; i++) {
    idx = 0;
    for (j = 0; j < 11; j++) {
      idx <<= 1;
      idx += (bits[(i * 11 + j) / 8] & (1 << (7 - ((i * 11 + j) % 8)))) > 0;
    }
    strcpy(p, wordlist[idx]);
    p += strlen(wordlist[idx]);
    *p = (i < mlen - 1) ? ' ' : 0;
    p++;
  }
  memzero(bits, sizeof(bits));

  return mnemo;
}

void mnemonic_clear(void) { memzero(mnemo, sizeof(mnemo)); }

// Constant-time comparison of two null-terminated strings up to max length.
// Returns 1 if equal, 0 if different.
// This function executes in constant time regardless of string content,
// providing resistance against timing side-channel attacks.
static int ct_word_eq(const char* input, const char* wordlist_word) {
  uint32_t diff = 0;
  uint32_t active = 0xFFFFFFFF;

  for (int i = 0; i < BIP39_MAX_WORD_LEN; i++) {
    uint8_t a = (uint8_t)input[i];
    uint8_t b = (uint8_t)wordlist_word[i];

    // Accumulate XOR difference only while active
    diff |= (a ^ b) & active;

    // Deactivate when either string terminates (constant-time mask update)
    // For a uint8_t value: if a==0, (a-1) sign-extends to 0xFFFFFFFF, >>31 = 1
    // If a!=0, (a-1) is in [0,254], >>31 = 0. Negating gives the mask.
    uint32_t a_term = -((uint32_t)(a - 1) >> 31);
    uint32_t b_term = -((uint32_t)(b - 1) >> 31);
    active &= ~(a_term | b_term);
  }

  // Return 1 if equal (diff == 0), 0 otherwise
  // When diff == 0: (0 - 1) = 0xFFFFFFFF, >> 8, & 1 = 1
  // When diff != 0: (diff - 1) >> 8, & 1 = 0 for diff in [1, 255]
  return (int)(1 & ((diff - 1) >> 8));
}

// Constant-time implementation to prevent side-channel attacks.
// This function always iterates through the entire wordlist for each word,
// uses constant-time string comparison, and avoids data-dependent branching
// when converting word indices to bits.
int mnemonic_to_bits(const char* mnemonic, uint8_t* bits) {
  if (!mnemonic) {
    return 0;
  }

  // Pad input into a fixed-size buffer so both parsing passes always iterate
  // exactly BIP39_MNEMONIC_MAX_WORDS * BIP39_MAX_WORD_LEN positions, removing
  // the mnemonic-length signal from the original while(mnemonic[i]) bounds.
  // BIP39_MAX_WORD_LEN counts one 8-byte word plus one following separator:
  // either a space between words or the trailing '\0' after the final word.
  // Therefore BIP39_MNEMONIC_MAX_WORDS * BIP39_MAX_WORD_LEN bytes are enough
  // for the longest valid mnemonic string, and this buffer keeps one extra
  // byte of headroom.
  char padded[BIP39_MNEMONIC_MAX_WORDS * BIP39_MAX_WORD_LEN + 1];
  memzero(padded, sizeof(padded));
  strncpy(padded, mnemonic, BIP39_MNEMONIC_MAX_WORDS * BIP39_MAX_WORD_LEN);

  uint32_t i = 0, n = 0;

  // Count words by counting spaces in a fixed-length pass.
  // Zeros past the real content contribute nothing, so
  // the count is correct without early termination.
  for (i = 0; i < BIP39_MNEMONIC_MAX_WORDS * BIP39_MAX_WORD_LEN; i++) {
    n += (uint32_t)(padded[i] == ' ');
  }

  if (padded[0] != '\0') {
    n++;  // one more word than spaces (non-empty input)
  }

  // check that number of words is valid for BIP-39:
  // (a) between 128 and 256 bits of initial entropy (12 - 24 words)
  // (b) number of bits divisible by 33 (1 checksum bit per 32 input bits)
  //     - that is, (n * 11) % 33 == 0, so n % 3 == 0
  if (n < 12 || n > 24 || (n % 3)) {
    memzero(padded, sizeof(padded));
    return 0;
  }

  char current_word[BIP39_MAX_WORD_LEN] = {0};
  uint32_t j = 0, k = 0, ki = 0, bi = 0;
  uint8_t result[32 + 1] = {0};
  uint32_t all_words_found = 0xFFFFFFFF;  // Track if all words were found
  uint32_t word_too_long = 0;             // Set if any word exceeds max length

  memzero(result, sizeof(result));
  i = 0;
  // Outer loop always runs BIP39_MNEMONIC_MAX_WORDS (24) iterations so that
  // the word count n does not influence total iteration count (timing).
  // Dummy iterations (w >= n) are masked out and do not affect the result.
  for (uint32_t w = 0; w < BIP39_MNEMONIC_MAX_WORDS; w++) {
    // active is 0xFFFFFFFF for real words (w < n), 0 for dummy iterations.
    uint32_t active = -(uint32_t)(w < n);
    j = 0;
    memzero(current_word, sizeof(current_word));

    // Fixed inner loop: always BIP39_MAX_WORD_LEN iterations (was -1, which
    // caused 8-char words to never set past_delim → spurious word_too_long).
    // Each read is bounds-checked to prevent OOB on crafted overlong input.
    uint32_t past_delim = 0;
    for (uint32_t ci = 0; ci < BIP39_MAX_WORD_LEN; ci++) {
      uint32_t idx = i + ci;
      char c = (idx < (uint32_t)(sizeof(padded) - 1)) ? padded[idx] : '\0';
      uint32_t is_delim = (uint32_t)((c == ' ') | (c == '\0'));
      past_delim |= is_delim;
      if (!past_delim) {
        current_word[j++] = c;
      }
    }

    // Advance i past the characters copied into current_word
    i += j;

    // If past_delim was never set the word overruns BIP39_MAX_WORD_LEN;
    // skip remaining characters.  Valid mnemonics never take this path.
    if (!past_delim) {
      word_too_long = 1;
      while (i < (uint32_t)(sizeof(padded) - 1) &&
             padded[i] != ' ' && padded[i] != '\0') {
        i++;
      }
    }

    // Skip the word delimiter (space) if present
    if (i < (uint32_t)(sizeof(padded) - 1) && padded[i] == ' ') {
      i++;
    }

    // Constant-time wordlist search: always iterate through ALL 2048 words
    // to prevent timing attacks that could reveal word indices
    uint32_t found_index = 0;
    uint32_t found = 0;

    for (k = 0; k < BIP39_WORDS; k++) {
      int eq = ct_word_eq(current_word, wordlist[k]);
      // Constant-time selection: mask is 0xFFFFFFFF if match, 0 otherwise
      uint32_t mask = -(uint32_t)eq;
      found_index = (found_index & ~mask) | (k & mask);
      found |= mask;
    }

    // Only require found for active (non-dummy) words.
    all_words_found &= (found | ~active);

    // Constant-time bit extraction; mask out dummy-word contributions so
    // they do not alter result bits beyond the n*11 active bits.
    for (ki = 0; ki < 11; ki++) {
      uint8_t bit = (uint8_t)((found_index >> (10 - ki)) & 1);
      result[bi / 8] |= (bit << (7 - (bi % 8))) & (uint8_t)(active & 0xFFu);
      bi++;
    }
  }

  // Check all words were found and no word exceeded the maximum length
  if (all_words_found == 0 || word_too_long) {
    memzero(padded, sizeof(padded));
    memzero(current_word, sizeof(current_word));
    memzero(result, sizeof(result));
    return 0;
  }

  memcpy(bits, result, sizeof(result));
  memzero(result, sizeof(result));
  memzero(current_word, sizeof(current_word));
  memzero(padded, sizeof(padded));

  // returns amount of entropy + checksum BITS
  return n * 11;
}

int mnemonic_check(const char *mnemonic) {
  uint8_t bits[32 + 1] = {0};
  int mnemonic_bits_len = mnemonic_to_bits(mnemonic, bits);
  if (mnemonic_bits_len != (12 * 11) && mnemonic_bits_len != (18 * 11) &&
      mnemonic_bits_len != (24 * 11)) {
    return 0;
  }
  int words = mnemonic_bits_len / 11;

  uint8_t checksum = bits[words * 4 / 3];
  sha256_Raw(bits, words * 4 / 3, bits);
  if (words == 12) {
    return (bits[0] & 0xF0) == (checksum & 0xF0);  // compare first 4 bits
  } else if (words == 18) {
    return (bits[0] & 0xFC) == (checksum & 0xFC);  // compare first 6 bits
  } else if (words == 24) {
    return bits[0] == checksum;  // compare 8 bits
  }
  return 0;
}

// passphrase must be at most 256 characters otherwise it would be truncated
void mnemonic_to_seed(const char *mnemonic, const char *passphrase,
                      uint8_t seed[512 / 8],
                      void (*progress_callback)(uint32_t current,
                                                uint32_t total)) {
  int mnemoniclen = strlen(mnemonic);
  int passphraselen = strnlen(passphrase, 256);
#if USE_BIP39_CACHE
  // check cache
  if (mnemoniclen < 256 && passphraselen < 64) {
    for (int i = 0; i < BIP39_CACHE_SIZE; i++) {
      if (!bip39_cache[i].set) continue;
      if (strcmp(bip39_cache[i].mnemonic, mnemonic) != 0) continue;
      if (strcmp(bip39_cache[i].passphrase, passphrase) != 0) continue;
      // found the correct entry
      memcpy(seed, bip39_cache[i].seed, 512 / 8);
      return;
    }
  }
#endif
  uint8_t salt[8 + 256] = {0};
  memcpy(salt, "mnemonic", 8);
  memcpy(salt + 8, passphrase, passphraselen);
  static CONFIDENTIAL PBKDF2_HMAC_SHA512_CTX pctx;
  pbkdf2_hmac_sha512_Init(&pctx, (const uint8_t *)mnemonic, mnemoniclen, salt,
                          passphraselen + 8, 1);
  if (progress_callback) {
    progress_callback(0, BIP39_PBKDF2_ROUNDS);
  }
  for (int i = 0; i < 16; i++) {
    pbkdf2_hmac_sha512_Update(&pctx, BIP39_PBKDF2_ROUNDS / 16);
    if (progress_callback) {
      progress_callback((i + 1) * BIP39_PBKDF2_ROUNDS / 16,
                        BIP39_PBKDF2_ROUNDS);
    }
  }
  pbkdf2_hmac_sha512_Final(&pctx, seed);
  memzero(salt, sizeof(salt));
#if USE_BIP39_CACHE
  // store to cache
  if (mnemoniclen < 256 && passphraselen < 64) {
    bip39_cache[bip39_cache_index].set = true;
    strcpy(bip39_cache[bip39_cache_index].mnemonic, mnemonic);
    strcpy(bip39_cache[bip39_cache_index].passphrase, passphrase);
    memcpy(bip39_cache[bip39_cache_index].seed, seed, 512 / 8);
    bip39_cache_index = (bip39_cache_index + 1) % BIP39_CACHE_SIZE;
  }
#endif
}

// binary search for finding the word in the wordlist
int mnemonic_find_word(const char *word) {
  int lo = 0, hi = BIP39_WORDS - 1;
  while (lo <= hi) {
    int mid = lo + (hi - lo) / 2;
    int cmp = strcmp(word, wordlist[mid]);
    if (cmp == 0) {
      return mid;
    }
    if (cmp > 0) {
      lo = mid + 1;
    } else {
      hi = mid - 1;
    }
  }
  return -1;
}

const char *mnemonic_complete_word(const char *prefix, int len) {
  // we need to perform linear search,
  // because we want to return the first match
  for (int k = 0; k < BIP39_WORDS; k++) {
    if (strncmp(wordlist[k], prefix, len) == 0) {
      return wordlist[k];
    }
  }
  return NULL;
}

const char *mnemonic_get_word(int index) {
  if (index >= 0 && index < BIP39_WORDS) {
    return wordlist[index];
  } else {
    return NULL;
  }
}

uint32_t mnemonic_word_completion_mask(const char *prefix, int len) {
  if (len <= 0) {
    return 0x3ffffff;  // all letters (bits 1-26 set)
  }
  uint32_t res = 0;
  for (int k = 0; k < BIP39_WORDS; k++) {
    const char *word = wordlist[k];
    if (strncmp(word, prefix, len) == 0 && word[len] >= 'a' &&
        word[len] <= 'z') {
      res |= 1 << (word[len] - 'a');
    }
  }
  return res;
}
