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
 * dispatch.c
 *
 * This code runs in an area of flash protected from viewing. It has limited entry
 * point (via a special callgate) and checks state carefully before running other stuff.
 *
 */
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "stm32h7xx_hal.h"

#include "delay.h"
#include "pprng.h"
#include "se.h"
#include "sha256.h"
#include "utils.h"

#include "dispatch.h"
#include "gpio.h"
#include "pins.h"
#include "se-atecc608a.h"
#include "version.h"

#define D1_AXISRAM_SIZE_MAX ((uint32_t)0x00080000U)

// memset4()
//
static inline void memset4(uint32_t* dest, uint32_t value, uint32_t byte_len) {
    for (; byte_len; byte_len -= 4, dest++) {
        *dest = value;
    }
}

// se_dispatch()
//
// A C-runtime compatible env. is running, so do some work.
//
__attribute__((used)) int se_dispatch(
    int method_num, uint8_t* buf_io, int len_in, uint32_t arg2, uint32_t incoming_sp, uint32_t incoming_lr) {
    int rv = 0;

    // Important:
    // - range check pointers so we aren't tricked into revealing our secrets
    // - check buf_io points to main SRAM, and not into us!
    // - range check len_in tightly
    // - calling convention only gives me enough for 4 args to this function, so
    //   using read/write in place.
    // - use arg2 use when a simple number is needed; never a pointer!
    // - mpy may provide a pointer to flash if we give it a qstr or small value, and if
    //   we're reading only, that's fine.

    if (len_in > 1024) {  // arbitrary max, increase as needed
        rv = ERANGE;
        goto fail;
    }

        // Use these macros
#define REQUIRE_OUT(x) \
    if (len_in < x) {  \
        goto fail;     \
    }

    // printf("se_dispatch() method_num=%d\n", method_num);

    // Random small delay to make cold-boot stepping attacks harder: 0 - 10,000us
    uint32_t us_to_delay = rng_sample() % 10000;
    delay_us(us_to_delay);

    switch (method_num) {
        case CMD_IS_BRICKED:
            // If the pairing secret doesn't work anymore, that means we've been bricked.
            rv = (se_pair_unlock() != 0);
            break;

        case CMD_READ_SE_SLOT: {
            // Read a dataslot directly. Will fail on
            // encrypted slots.
            if (len_in != 4 && len_in != 32 && len_in != 72) {
                rv = ERANGE;
            } else {
                REQUIRE_OUT(4);

                if (se_read_data_slot(arg2 & 0xf, buf_io, len_in)) {
                    rv = EIO;
                }
            }

            break;
        }

        case CMD_GET_ANTI_PHISHING_WORDS: {
            // Provide the 2 words for anti-phishing.
            REQUIRE_OUT(MAX_PIN_LEN);

            // arg2: length of pin.
            if ((arg2 < 1) || (arg2 > MAX_PIN_LEN)) {
                rv = ERANGE;
            } else {
                if (anti_phishing_words((char*)buf_io, arg2, (uint32_t*)buf_io)) {
                    rv = EIO;
                }
            }
            break;
        }

        case CMD_GET_SUPPLY_CHAIN_VALIDATION_WORDS: {
            // Provide a hash to use for the supply chain validation words'
            if (supply_chain_validation_words((char*)buf_io, arg2, (uint32_t*)buf_io)) {
                rv = EIO;
            }
            break;
        }

        case CMD_GET_RANDOM_BYTES:
            rng_buffer(buf_io, len_in);
            break;

        case CMD_PIN_CONTROL: {
            // Try login w/ PIN.
            REQUIRE_OUT(PIN_ATTEMPT_SIZE_V1);
            pinAttempt_t* args = (pinAttempt_t*)buf_io;

            switch (arg2) {
                case PIN_SETUP:
                    rv = pin_setup_attempt(args);
                    break;
                case PIN_ATTEMPT:
                    rv = pin_login_attempt(args);
                    break;
                case PIN_CHANGE:
                    rv = pin_change(args);
                    break;
                case PIN_GET_SECRET:
                    rv = pin_fetch_secret(args);
                    break;

                default:
                    rv = ENOENT;
                    break;
            }
            break;
        }

        case CMD_GET_SE_CONFIG:
            // Read out entire config dataspace
            REQUIRE_OUT(128);

            rv = se_config_read(buf_io);
            if (rv) {
                rv = EIO;
            }
            break;

        default:
            rv = ENOENT;
            break;
    }
#undef REQUIRE_IN_ONLY
#undef REQUIRE_OUT

fail:
    // Precaution: we don't want to leave ATECC508A authorized for any specific keys,
    // perhaps due to an error path we didn't see. Always reset the chip.
    se_reset_chip();

    return rv;
}
