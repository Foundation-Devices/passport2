// SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//
// SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
// SPDX-License-Identifier: GPL-3.0-only
//
/*
 * (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
 * and is covered by GPLv3 license found in COPYING.
 *
 * SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include "stm32h7xx_hal.h"
#include "stm32h7xx_hal_uart.h"
#include "stm32h7xx_hal_uart_ex.h"

#include "pprng.h"
#include "se-config.h"
#include "se.h"
#include "secrets.h"
#include "sha256.h"
#include "utils.h"

#include "se-atecc608a.h"

// Selectable debug level; keep them as comments regardless
#if 0
// break on any error: not helpful since some are normal
#define ERR(msg) BREAKPOINT;
#define ERRV(val, msg) BREAKPOINT;
#else
#define ERR(msg)
#define ERRV(val, msg)
#endif

// keep this in place.
#define RET_IF_BAD(rv)     \
    do {                   \
        if (rv) return rv; \
    } while (0)

bool se_probe() {
    int chk;

    se_sleep();
    se_wake();

    // Expect 0x11
    chk = se_read1();
    if (chk != SE_AFTER_WAKE) return false;
    se_sleep();

    return true;
}

// Do Info(p1=2) command, and return result.
//
uint16_t se_get_info(void) {
    int rc;

    // not doing error checking here
    se_write(OP_Info, 0x2, 0, NULL, 0);
    // note: always returns 4 bytes, but most are garbage and unused.
    uint8_t tmp[4];
    rc = se_read(tmp, 4);
    se_sleep();
    if (rc < 0) return -1;

    return (tmp[0] << 8) | tmp[1];
}

// Load Tempkey with a specific value. Resulting Tempkey cannot be
// used with many commands/keys, but is needed for signing.
//
int se_load_nonce(uint8_t nonce[32]) {
    uint8_t rc;

    // p1=3
    se_write(OP_Nonce, 3, 0, nonce, 32);  // 608a ok
    rc = se_read1();
    se_sleep();
    if (rc != 0) return -1;
    return 0;
}

// Sign a message (already digested)
//
int se_sign(uint8_t keynum, uint8_t msg_hash[32], uint8_t signature[64]) {
    int rc;

    rc = se_load_nonce(msg_hash);
    if (rc < 0) return -1;

    se_write(OP_Sign, 0x80, keynum, NULL, 0);
    rc = se_read(signature, 64);
    se_sleep();
    if (rc < 0) return -1;

    return 0;
}

// Use old SHA256 command from 508A, but with new flags.
//
int se_hmac32(uint8_t keynum, uint8_t msg[32], uint8_t digest[32]) {
    int rc;

    // Start SHA w/ HMAC setup
    se_write(OP_SHA, 4, keynum, NULL, 0);  // 4 = HMAC_Init
    rc = se_read1();
    if (rc != 0) return -1;

    // send the contents to be hashed
    se_write(OP_SHA, (3 << 6) | 2, 32, msg, 32);  // 2 = Finalize, 3=Place output
    rc = se_read(digest, 32);
    se_sleep();
    return rc;
}

// Return the serial number: it's 9 bytes, altho 3 are fixed.
//
int se_get_serial(uint8_t serial[6]) {
    int     rc;
    uint8_t temp[32];

    se_write(OP_Read, 0x80, 0x0, NULL, 0);
    rc = se_read(temp, 32);
    se_sleep();
    if (rc < 0) return -1;

    // reformat to 9 bytes.
    uint8_t ts[9];
    memcpy(ts, &temp[0], 4);
    memcpy(&ts[4], &temp[8], 5);

    // check the hard-coded values
    if ((ts[0] != 0x01) || (ts[1] != 0x23) || (ts[8] != 0xEE)) return 1;

    // save only the unique bits.
    memcpy(serial, ts + 2, 6);

    return 0;
}

int se_destroy_key(int keynum) {
    int     rc;
    uint8_t numin[20];

    // Load tempkey with a known (random) nonce value
    rng_buffer(numin, sizeof(numin));
    se_write(OP_Nonce, 0, 0, numin, 20);

    // Nonce command returns the RNG result, not contents of TempKey,
    // but since we are destroying, no need to calculate what it is.
    uint8_t randout[32];
    rc = se_read(randout, 32);
    if (rc < 0) return -1;

    // do a "DeriveKey" operation, based on that!
    se_write(OP_DeriveKey, 0x00, keynum, NULL, 0);
    rc = se_read1();
    se_sleep();
    if (rc != 0) return -1;
    return 0;
}

// Do on-chip hashing, with lots of iterations.
//
// - using HMAC-SHA256 with keys that are known only to the 608a.
// - rate limiting factor here is communication time w/ 608a, not algos.
// - caution: result here is not confidential
// - cost of each iteration, approximately: 8ms
// - but our time to do each iteration is limited by software SHA256 in se_pair_unlock
//
int se_stretch_iter(const uint8_t start[32], uint8_t end[32], int iterations) {
    if (start == end) {
        return -1;
    }

    memcpy(end, start, 32);

    for (int i = 0; i < iterations; i++) {
        // must unlock again, because pin_stretch is an auth'd key
        if (se_pair_unlock()) return -2;

        int rv = se_hmac32(KEYNUM_pin_stretch, end, end);
        if (rv < 0) return -1;

        LV_REFRESH();
    }

    return 0;
}

// Apply HMAC using secret in chip as a HMAC key, then encrypt
// the result a little because read in clear over bus.
//
int se_mixin_key(uint8_t keynum, uint8_t start[32], uint8_t end[32]) {
    int rc;

    if (start == end) {
        return -1;
    }

    rc = se_pair_unlock();
    if (rc < 0) return -1;

    if (keynum != 0) {
        rc = se_hmac32(keynum, start, end);
        if (rc < 0) return -1;
    } else {
        memset(end, 0, 32);
    }

    // Final value was just read over bus w/o any protection, but
    // we won't be using that, instead, mix in the pairing secret.
    //
    // Concern: what if mitm gave us some zeros or other known pattern here. We will
    // use the value provided in cleartext[sic--it's not] write back shortly (to test it).
    // Solution: one more SHA256, and to be safe, mixin lots of values!

    SHA256_CTX ctx;

    sha256_init(&ctx);
    sha256_update(&ctx, rom_secrets->pairing_secret, 32);
    sha256_update(&ctx, start, 32);
    sha256_update(&ctx, &keynum, 1);
    sha256_update(&ctx, end, 32);
    sha256_final(&ctx, end);

    return 0;
}
