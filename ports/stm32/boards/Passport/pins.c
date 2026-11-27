// SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundation.xyz>
// SPDX-License-Identifier: GPL-3.0-or-later
//
// SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
// SPDX-License-Identifier: GPL-3.0-only
//
/*
 * (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
 * and is covered by GPLv3 license found in COPYING.
 *
 * pins.c -- PIN codes and security issues
 *
 */
#include <stdio.h>
#include <string.h>

#include "delay.h"
#include "pprng.h"
#include "se.h"
#include "secrets.h"
#include "sha256.h"
#include "utils.h"

#include "debug-utils.h"
#include "pins.h"
#include "se-config.h"

// Number of iterations for KDF
#define KDF_ITER_WORDS 2
#define KDF_ITER_PIN 8  // about ? seconds (measured in-system)

// We try to keep at least this many PIN attempts available to legit users
// - challenge: comparitor resolution is only 32 units (5 LSB not implemented)
// - solution: adjust both the target and counter (upwards)
#define MAX_TARGET_ATTEMPTS 21

// Pretty sure it doesn't matter, but adding some salt into our PIN->bytes[32] code
// based on the purpose of the PIN code.
//
#define PIN_PURPOSE_NORMAL 0x334d1858
#define PIN_PURPOSE_ANTI_PHISH_WORDS 0x2e6d6773
#define PIN_PURPOSE_SUPPLY_CHAIN_WORDS 0xb6c9f792

// Keep this around after the user logs in successfully
uint8_t g_cached_main_pin[32];

// Hash up a PIN for indicated purpose.
static void pin_hash(const char* pin, int pin_len, uint8_t result[32], uint32_t purpose);

// pin_is_blank()
//
// Is a specific PIN defined already? Not safe to expose this directly to callers!
//
static bool pin_is_blank(uint8_t keynum) {
    uint8_t blank[32] = {0};

    se_reset_chip();
    se_pair_unlock();

    // Passing this check with zeros, means PIN was blank.
    // Failure here means nothing (except not blank).
    int is_blank = (se_checkmac_hard(keynum, blank) == 0);

    // CAUTION? We've unlocked something maybe, but it's blank, so...
    se_reset_chip();

    return is_blank;
}

// is_main_pin()
//
// Do the checkmac thing using a PIN, and if it works, great.
//
static bool is_main_pin(const uint8_t digest[32], int* pin_kn) {
    int kn = KEYNUM_pin_hash;

    se_reset_chip();
    se_pair_unlock();

    if (se_checkmac_hard(kn, digest) == 0) {
        *pin_kn = kn;

        return true;
    }

    return false;
}

// pin_hash()
//
// Hash up a string of digits in 32-byte goodness.
//
static void pin_hash(const char* pin, int pin_len, uint8_t result[32], uint32_t purpose) {
    // Used for supply chain validation too...not sure if that is less than MAX_PIN_LEN yet.
    // ASSERT(pin_len <= MAX_PIN_LEN);

    if (pin_len == 0) {
        // zero-length PIN is considered the "blank" one: all zero
        memset(result, 0, 32);
        return;
    }

    SHA256_CTX ctx;
    sha256_init(&ctx);

    sha256_update(&ctx, rom_secrets->pairing_secret, 32);
    sha256_update(&ctx, (uint8_t*)&purpose, 4);
    sha256_update(&ctx, (uint8_t*)pin, pin_len);
    sha256_update(&ctx, rom_secrets->otp_key, 32);

    sha256_final(&ctx, result);

    // and a second-sha256 on that, just in case.
    sha256_init(&ctx);
    sha256_update(&ctx, result, 32);
    sha256_final(&ctx, result);
}

// pin_hash_attempt()
//
// Go from PIN to heavily hashed 32-byte value, suitable for testing against device.
//
// - call with target_kn == 0 to return a mid-state that can be used for main pin
//
static int pin_hash_attempt(uint8_t target_kn, const char* pin, int pin_len, uint8_t result[32]) {
    uint8_t tmp[32];

    if (pin_len == 0) {
        // zero len PIN is the "blank" value: all zeros, no hashing
        memset(result, 0, 32);
        return 0;
    }

    // quick local hashing
    pin_hash(pin, pin_len, tmp, PIN_PURPOSE_NORMAL);

    // main pin needs mega hashing
    int rv = se_stretch_iter(tmp, result, KDF_ITER_PIN);
    if (rv) return EPIN_SE_FAIL;

    // CAUTION: at this point, we just read the value off the bus
    // in clear text. Don't use that value directly.

    if (target_kn == 0) {
        // let the caller do either/both of the below mixins
        return 0;
    }

    memcpy(tmp, result, 32);
    if (target_kn == KEYNUM_pin_hash) {
        se_mixin_key(KEYNUM_pin_attempt, tmp, result);
    } else {
        se_mixin_key(0, tmp, result);
    }

    return 0;
}

// pin_cache_get_key()
//
void pin_cache_get_key(uint8_t key[32]) {
    // per-boot unique key.
    SHA256_CTX ctx;

    sha256_init(&ctx);
    sha256_update(&ctx, rom_secrets->hash_cache_secret, 32);

    sha256_final(&ctx, key);
}

// pin_cache_save()
//
static int pin_cache_save(pinAttempt_t* args, uint8_t* digest) {
    // encrypt w/ rom secret + SRAM seed value
    uint8_t value[32];

    if (!check_all_zeros(digest, 32)) {
        pin_cache_get_key(value);
        xor_mixin(value, digest, 32);
    } else {
        memset(value, 0, 32);
    }

    if (args->magic_value != PA_MAGIC_V1) {
        return EPIN_BAD_MAGIC;
    }

    memcpy(args->cached_main_pin, value, 32);

    // Keep a copy around so we can do other auth'd actions later like set a user firmware pubkey
    memcpy(g_cached_main_pin, value, 32);
    return 0;
}

// pin_cache_restore()
//
int pin_cache_restore(pinAttempt_t* args, uint8_t digest[32]) {
    // decrypt w/ rom secret + SRAM seed value
    if (args->magic_value != PA_MAGIC_V1) {
        return EPIN_BAD_MAGIC;
    }

    memcpy(digest, args->cached_main_pin, 32);

    if (!check_all_zeros(digest, 32)) {
        uint8_t key[32];
        pin_cache_get_key(key);
        xor_mixin(digest, key, 32);
    }

    return 0;
}

// anti_phishing_words()
//
// Do HMAC(words secret) and return digest
//
// CAUTIONS:
// - rate-limited by the chip, since it takes many iterations of HMAC(key we dont have)
// - hash generated is shown on bus (but further hashing happens after that)
//
int anti_phishing_words(const char* pin_prefix, int prefix_len, uint32_t* result) {
    uint8_t tmp[32];
    uint8_t digest[32];

    // hash it up, a little
    pin_hash(pin_prefix, prefix_len, tmp, PIN_PURPOSE_ANTI_PHISH_WORDS);

    // Using 608a, we can do key stretching to get good built-in delays
    int rv = se_stretch_iter(tmp, digest, KDF_ITER_WORDS);

    se_reset_chip();
    if (rv) return -1;

    // Return all 32 bytes - will be used as input to bip32.from_data()
    // This is OK because MAX_PIN_LEN is 32, and the result buf is the same
    // as the pin_prefix buf.
    memcpy(result, digest, 32);

    return 0;
}

// supply_chain_validation_words()
//
// Perform HMAC_SHA256 using SE and supply chain slot. This hashes the given
// data with the secret value in the SE and returns the result.
//
// Caller will use these 32 bytes to generate words.
//
int supply_chain_validation_words(const char* data, int data_len, uint32_t* result) {
    se_pair_unlock();

    int rc = se_hmac32(KEYNUM_supply_chain, (uint8_t*)data, (uint8_t*)result);
    if (rc < 0) {
        return -1;
    }
    return 0;
}

// _hmac_attempt()
//
// Maybe should be proper HMAC from fips std? Can be changed later.
//
static void _hmac_attempt(const pinAttempt_t* args, uint8_t result[32]) {
    SHA256_CTX ctx;

    sha256_init(&ctx);
    sha256_update(&ctx, rom_secrets->pairing_secret, 32);
    sha256_update(&ctx, (uint8_t*)args, offsetof(pinAttempt_t, hmac));
    sha256_final(&ctx, result);

    // and a second-sha256 on that, just in case.
    sha256_init(&ctx);
    sha256_update(&ctx, result, 32);
    sha256_final(&ctx, result);
}

// _validate_attempt()
//
static int _validate_attempt(pinAttempt_t* args, bool first_time) {
    if (first_time) {
        // no hmac needed for setup call
    } else {
        // if hmac is defined, better be right.
        uint8_t actual[32];

        _hmac_attempt(args, actual);

        // printf("args->hmac=%02x %02x %02x %02x\n", args->hmac[0], args->hmac[1], args->hmac[2], args->hmac[3] );
        // printf("actual    =%02x %02x %02x %02x\n", actual[0], actual[1], actual[2], actual[3]);
        if (!check_equal(actual, args->hmac, 32)) {
            // hmac is wrong?
            return EPIN_HMAC_FAIL;
        }
    }

    // check fields.
    if (args->magic_value == PA_MAGIC_V1) {
        // ok
    } else {
        return EPIN_BAD_MAGIC;
    }

    // check fields
    if (args->pin_len > MAX_PIN_LEN) return EPIN_RANGE_ERR;
    if (args->old_pin_len > MAX_PIN_LEN) return EPIN_RANGE_ERR;
    if (args->new_pin_len > MAX_PIN_LEN) return EPIN_RANGE_ERR;
    if ((args->change_flags & CHANGE__MASK) != args->change_flags) return EPIN_RANGE_ERR;

    return 0;
}

// _sign_attempt()
//
// Provide our "signature" validating struct contents as coming from us.
//
static void _sign_attempt(pinAttempt_t* args) {
    _hmac_attempt(args, args->hmac);
}

// _read_slot_as_counter()
//
static int _read_slot_as_counter(uint8_t slot, uint32_t* dest) {
    // Read (typically a) counter value held in a dataslot.
    // Important that this be authenticated.
    //
    // - using first 32-bits only, others will be zero/ignored
    // - but need to read whole thing for the digest check

    uint32_t padded[32 / 4] = {0};
    se_pair_unlock();
    if (se_read_data_slot(slot, (uint8_t*)padded, 32)) return -1;

    uint8_t tempkey[32];
    se_pair_unlock();
    if (se_gendig_slot(slot, (const uint8_t*)padded, tempkey)) return -1;

    if (!se_is_correct_tempkey(tempkey)) {
        return -1;
    }

    *dest = padded[0];

    return 0;
}

// get_last_success()
//
// Read state about previous attempt(s) from AE. Calculate number of failures,
// and how many attempts are left. The need for verifing the values from AE is
// not really so strong with the 608a, since it's all enforced on that side, but
// we'll do it anyway.
//
static int __attribute__((noinline)) get_last_success(pinAttempt_t* args) {
    const int slot = KEYNUM_lastgood;

    se_pair_unlock();

    // Read counter value of last-good login. Important that this be authenticated.
    // - using first 32-bits only, others will be zero
    uint32_t padded[32 / 4] = {0};
    if (se_read_data_slot(slot, (uint8_t*)padded, 32)) return -1;

    uint8_t tempkey[32];
    se_pair_unlock();
    if (se_gendig_slot(slot, (const uint8_t*)padded, tempkey)) return -2;

    if (!se_is_correct_tempkey(tempkey)) {
        return -3;
    }

    // Read two values from data slots
    uint32_t lastgood = 0, match_count = 0, counter = 0;
    if (_read_slot_as_counter(KEYNUM_lastgood, &lastgood)) return -4;
    if (_read_slot_as_counter(KEYNUM_match_count, &match_count)) return -5;

    // Read the monotonically-increasing counter
    if (se_get_counter(&counter, 0)) return -6;

    if (lastgood > counter) {
        // monkey business, but impossible, right?!
        args->num_fails = 99;
    } else {
        args->num_fails = counter - lastgood;
    }

    // NOTE: 5LSB of match_count should be stored as zero.
    match_count &= ~31;
    if (counter < match_count) {
        // typical case: some number of attempts left before death
        args->attempts_left = match_count - counter;
    } else if (counter >= match_count) {
        // we're a brick now, but maybe say that nicer to customer
        args->attempts_left = 0;
    }

    return 0;
}

// warmup_ae()
//
static int warmup_se(void) {
    for (int retry = 0; retry < 5; retry++) {
        if (se_probe() == true) {
            // Success
            break;
        }
    }

    if (se_pair_unlock()) return -1;

    // reset watchdog timer
    se_keep_alive();

    return 0;
}

// pin_setup_attempt()
//
// Get number of failed attempts on a PIN, since last success. Calculate
// required delay, and setup initial struct for later attempts.
//
int pin_setup_attempt(pinAttempt_t* args) {
    if (sizeof(pinAttempt_t) != PIN_ATTEMPT_SIZE_V1) {
        return EPIN_BAD_REQUEST;
    }

    int rv = _validate_attempt(args, true);
    if (rv) return rv;

    // wipe most of struct, keep only what we expect and want!
    // - old firmware wrote zero to magic before this point, and so we set it here

    char pin_copy[MAX_PIN_LEN];
    int  pin_len = args->pin_len;
    memcpy(pin_copy, args->pin, pin_len);

    memset(args, 0, PIN_ATTEMPT_SIZE_V1);

    args->state_flags = 0;
    args->magic_value = PA_MAGIC_V1;
    args->pin_len     = pin_len;
    memcpy(args->pin, pin_copy, pin_len);

    // unlock the AE chip
    int result = warmup_se();
    if (result) {
        printf("pin_setup_attempt() ERROR: 1  result = %d\n", result);
        return EPIN_I_AM_BRICK;
    }

    // Read counters, and calc number of PIN attempts left
    result = get_last_success(args);
    if (result) {
        printf("pin_setup_attempt() ERROR: 2  result = %d\n", result);
        se_reset_chip();

        return EPIN_SE_FAIL;
    }

    // delays now handled by chip and our KDF process directly
    args->delay_required = 0;
    args->delay_achieved = 0;

    // need to know if we are blank/unused device
    result = pin_is_blank(KEYNUM_pin_hash);
    if (result) {
        printf("pin_setup_attempt() ERROR: 3 (BLANK PIN!): result = %d\n", result);
        args->state_flags |= PA_SUCCESSFUL | PA_IS_BLANK;

        // We need to save this 'zero' value because it's encrypted, and/or might be
        // un-initialized memory.
        uint8_t zeros[32] = {0};
        result            = pin_cache_save(args, zeros);
        if (result) {
            return result;
        }

        // need legit value in here
        args->private_state = (rng_sample() & ~1) ^ rom_secrets->hash_cache_secret[0];
    }

    _sign_attempt(args);

    return 0;
}

// updates_for_good_login()
//
static int updates_for_good_login(uint8_t digest[32]) {
    // User got the main PIN right: update the attempt counters,
    // to document this (lastgood) and also bump the match counter if needed

    uint32_t count;
    int      rv = se_get_counter(&count, 0);
    if (rv) goto fail;

    // The weird math here is because the match count slot in the SE ignores the least
    // significant 5 bits, so the match count must be a multiple of 32. When a good
    // login occurs, we need to update both the match count and the monotonic counter.
    //
    // For example, if the monotonic counter was 19 and the match count was 32, and the
    // user just provided the correct PIN, you would normally just bump the match count
    // to 33, but since that is not a multiple of 32, we have to bump it to 64. That
    // would then give 64-19 = 45 login attempts remaining though, so further down,
    // in se_add_counter(), we bump the monotonic counter in a loop until there are
    // MAX_TARGET_ATTEMPTS left (match count - counter0 = MAX_TARGET_ATTEMPTS_LEFT).
    uint32_t mc = (count + MAX_TARGET_ATTEMPTS + 32) & ~31;

    int bump = (mc - MAX_TARGET_ATTEMPTS) - count;

    // The SE won't let the counter go past the match count, so we have to update the
    // match count first.

    // Set the new "match count"
    {
        uint32_t tmp[32 / 4] = {mc, mc};
        rv                   = se_encrypted_write(KEYNUM_match_count, KEYNUM_pin_hash, digest, (void*)tmp, 32);
        if (rv) goto fail;
    }

    // Increment the counter a bunch to get to that-13
    uint32_t new_count = 0;
    rv                 = se_add_counter(&new_count, 0, bump);
    if (rv) goto fail;

    // Update the "last good" counter
    {
        uint32_t tmp[32 / 4] = {new_count, 0};
        rv                   = se_encrypted_write(KEYNUM_lastgood, KEYNUM_pin_hash, digest, (void*)tmp, 32);
        if (rv) goto fail;
    }

    // NOTE: Some or all of the above writes could be blocked (trashed) by an
    // active MitM attacker, but that would be pointless since these are authenticated
    // writes, which have a MAC. They can't change the written value, due to the MAC, so
    // all they can do is block the write, and not control it's value. Therefore, they will
    // just be reducing attempt. Also, rate limiting not affected by anything here.

    return 0;

fail:
    se_reset_chip();
    return EPIN_SE_FAIL;
}

// pin_login_attempt()
//
// Do the PIN check, and return a value. Or fail.
//
int pin_login_attempt(pinAttempt_t* args) {
    int rv = _validate_attempt(args, false);
    if (rv) {
        printf("pin_login_attempt 1: rv=%d\n", rv);
        return rv;
    }

    if (args->state_flags & PA_SUCCESSFUL) {
        printf("pin_login_attempt 2\n");
        // already worked, or is blank
        return EPIN_WRONG_SUCCESS;
    }

    // unlock the AE chip
    if (warmup_se()) {
        printf("pin_login_attempt 3\n");
        return EPIN_I_AM_BRICK;
    }

    int pin_kn    = -1;
    int secret_kn = -1;

    // hash up the pin now, assuming we'll use it on main PIN
    uint8_t mid_digest[32], digest[32];
    rv = pin_hash_attempt(0, args->pin, args->pin_len, mid_digest);
    if (rv) {
        printf("pin_login_attempt 4: rv=%d\n", rv);
        return EPIN_SE_FAIL;
    }

    // Do mixin
    rv = se_mixin_key(0, mid_digest, digest);
    if (rv) {
        printf("pin_login_attempt 5: rv=%d\n", rv);
        return EPIN_SE_FAIL;
    }

    // Register an attempt on the pin
    rv = se_mixin_key(KEYNUM_pin_attempt, mid_digest, digest);
    if (rv) {
        printf("pin_login_attempt 6: rv=%d\n", rv);
        return EPIN_SE_FAIL;
    }

    if (!is_main_pin(digest, &pin_kn)) {
        // Update args with latest attempts remaining
        get_last_success(args);
        printf("BAD PIN: attempts_left: %lu  num_fails: %lu\n", args->attempts_left, args->num_fails);

        // PIN code is just wrong.
        // - nothing to update, since the chip's done it already
        return EPIN_AUTH_FAIL;
    }

    secret_kn = KEYNUM_seed;

    // change the various counters, since this worked
    rv = updates_for_good_login(digest);
    if (rv) {
        // Update args with latest attempts remaining
        get_last_success(args);
        printf("GOOD PIN: attempts_left: %lu  num_fails: %lu\n", args->attempts_left, args->num_fails);
        return EPIN_SE_FAIL;
    }

    // SUCCESS! "digest" holds a working value. Save it.
    rv = pin_cache_save(args, digest);
    if (rv) {
        return rv;
    }

    // ASIDE: even if the above was bypassed, the following code will
    // fail when it tries to read/update the corresponding slots in the SE

    // mark as success
    args->state_flags = PA_SUCCESSFUL;

    // these are constants, and user doesn't care because they got in... but consistency.
    args->num_fails     = 0;
    args->attempts_left = MAX_TARGET_ATTEMPTS;

    // I used to always read the secret, since it's so hard to get to this point,
    // but now just indicating if zero or non-zero so that we don't contaminate the
    // caller w/ sensitive data that they may not want yet.
    {
        uint8_t ts[SE_SECRET_LEN];

        rv = se_encrypted_read(secret_kn, pin_kn, digest, ts, SE_SECRET_LEN);
        if (rv) {
            printf("pin_login_attempt 9: rv=%d\n", rv);
            se_reset_chip();

            return EPIN_SE_FAIL;
        }
        se_reset_chip();

        if (check_all_zeros(ts, SE_SECRET_LEN)) {
            args->state_flags |= PA_ZERO_SECRET;
        }
    }

    lv_refresh();

    _sign_attempt(args);

    return 0;
}

// pin_change()
//
// Change the PIN and/or secrets (must also know the value, or it must be blank)
//
int pin_change(pinAttempt_t* args) {
    // Validate args and signature
    int rv = _validate_attempt(args, false);
    if (rv) {
        return rv;
    }

    if ((args->state_flags & PA_SUCCESSFUL) != PA_SUCCESSFUL) {
        // must come here with a successful PIN login (so it's rate limited nicely)
        return EPIN_WRONG_SUCCESS;
    }

    if (args->state_flags & PA_IS_BLANK) {
        // if blank, must provide blank value
        if (args->pin_len) return EPIN_RANGE_ERR;
    }

    // Look at change flags.
    const uint32_t cf = args->change_flags;

    // Must be here to do something.
    if (cf == 0) {
        return EPIN_RANGE_ERR;
    }

    // unlock the AE chip
    if (warmup_se()) {
        return EPIN_I_AM_BRICK;
    }

    // what pin do they need to know to make their change?
    int required_kn = KEYNUM_pin_hash;
    // what slot (key number) are updating?
    int target_slot = -1;

    // No real need to re-prove PIN knowledge.
    // If they tricked us to get to this point, doesn't matter as
    // below the SE validates it all again.

    if (cf & CHANGE_WALLET_PIN) {
        target_slot = KEYNUM_pin_hash;
    } else if (cf & CHANGE_SECRET) {
        target_slot = KEYNUM_seed;
    } else {
        return EPIN_RANGE_ERR;
    }

    // Determine they know hash protecting the secret/pin to be changed.
    uint8_t required_digest[32];  // Construct hash of pin needed.

    // Use pin cache when changing the secret, otherwise it's a pin change and we rehash
    if (cf & CHANGE_SECRET) {
        // Restore cached version of PIN digest: faster
        pin_cache_restore(args, required_digest);
    } else {
        pin_hash_attempt(required_kn, args->old_pin, args->old_pin_len, required_digest);

        // Check the old pin provided, is right.
        se_pair_unlock();
        if (se_checkmac(required_kn, required_digest)) {
            // they got old PIN wrong, we won't be able to help them
            se_reset_chip();

            // NOTE: altho we are changing flow based on result of ae_checkmac() here,
            // if the response is faked by an active bus attacker, it doesn't matter
            // because the change to the dataslot below will fail due to wrong PIN.

            return EPIN_OLD_AUTH_FAIL;
        }
    }

    // Calculate new PIN hashed value: will be slow for main pin.
    if (cf & CHANGE_WALLET_PIN) {
        uint8_t new_digest[32];
        rv = pin_hash_attempt(required_kn, args->new_pin, args->new_pin_len, new_digest);
        if (rv) {
            goto se_fail;
        }
        // dump_buf(required_digest, 32);
        if (se_encrypted_write(target_slot, required_kn, required_digest, new_digest, 32)) {
            goto se_fail;
        }

        if (target_slot == required_kn) {
            memcpy(required_digest, new_digest, 32);
        }

        if (target_slot == KEYNUM_pin_hash) {
            // main pin is changing; reset counter to zero (good login) and our cache
            rv = pin_cache_save(args, new_digest);
            if (rv) {
                return rv;
            }

            updates_for_good_login(new_digest);
        }
    }

    // Record new secret.
    // Note the required_digest might have just changed above.
    if (cf & CHANGE_SECRET) {
        int secret_kn = KEYNUM_seed;

        bool is_all_zeros = check_all_zeros(args->secret, SE_SECRET_LEN);

        // encrypt new secret, but only if not zeros!
        uint8_t tmp[SE_SECRET_LEN] = {0};
        if (!is_all_zeros) {
            xor_mixin(tmp, rom_secrets->otp_key, SE_SECRET_LEN);
            xor_mixin(tmp, args->secret, SE_SECRET_LEN);
        }

        // dump_buf(required_digest, 32);
        if (se_encrypted_write(secret_kn, required_kn, required_digest, tmp, SE_SECRET_LEN)) {
            goto se_fail;
        }

        // update the zero-secret flag to be correct.
        if (cf & CHANGE_SECRET) {
            if (is_all_zeros) {
                args->state_flags |= PA_ZERO_SECRET;
            } else {
                args->state_flags &= ~PA_ZERO_SECRET;
            }
        }
    }

    se_reset_chip();

    // need to pass back the (potentially) updated cache value and some flags.
    _sign_attempt(args);

    return 0;

se_fail:
    se_reset_chip();

    return EPIN_SE_FAIL;
}

// pin_fetch_secret()
//
// To encourage not keeping the secret in memory, a way to fetch it after already
// have proven you know the PIN.
//
int pin_fetch_secret(pinAttempt_t* args) {
    // Validate args and signature
    int rv = _validate_attempt(args, false);
    if (rv) return rv;

    if ((args->state_flags & PA_SUCCESSFUL) != PA_SUCCESSFUL) {
        // must come here with a successful PIN login (so it's rate limited nicely)
        return EPIN_WRONG_SUCCESS;
    }

    // fetch the already-hashed pin
    // - no real need to re-prove PIN knowledge.
    // - if they tricked us, doesn't matter as below the SE validates it all again
    uint8_t digest[32];
    rv = pin_cache_restore(args, digest);
    if (rv) {
        return rv;
    }

    int pin_kn      = KEYNUM_pin_hash;
    int secret_slot = KEYNUM_seed;

    // read out the secret that corresponds to the pin
    rv = se_encrypted_read(secret_slot, pin_kn, digest, args->secret, SE_SECRET_LEN);

    bool is_all_zeros = check_all_zeros(args->secret, SE_SECRET_LEN);

    // decrypt the secret, but only if not zeros!
    if (!is_all_zeros) xor_mixin(args->secret, rom_secrets->otp_key, SE_SECRET_LEN);

    se_reset_chip();

    if (rv) return EPIN_SE_FAIL;

    return 0;
}

// EOF
