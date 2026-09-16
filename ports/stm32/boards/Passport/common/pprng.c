// SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundation.xyz>
// SPDX-License-Identifier: GPL-3.0-or-later
//
// SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
// SPDX-License-Identifier: GPL-3.0-only
//
/*
 * (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
 * and is covered by GPLv3 license found in COPYING.
 */
#include <stdbool.h>
#include <string.h>

#include "stm32h7xx_hal.h"

#include "delay.h"
#include "pprng.h"
#include "utils.h"

// Bound the number of polling attempts.
// Firmware and bootloader configure a 480 MHz CPU. Target roughly 10 ms using
// an unmeasured estimate of 10 CPU cycles per no-data poll: 480 MHz * 10 ms / 10.
// This is not a calibrated timeout; MMIO stalls, interrupts, and the longer
// zero/duplicate retry path affect elapsed time.
#define RNG_MAX_POLL_ATTEMPTS 480000U
#define RNG_MAX_RECOVERY_ATTEMPTS 3U

static bool rng_recover_seed_error(uint32_t* recovery_attempts) {
    while (*recovery_attempts < RNG_MAX_RECOVERY_ATTEMPTS) {
        (*recovery_attempts)++;

        // ST's seed-error recovery sequence (RM0433 section 34.3.7): clear
        // SEIS and flush 12 words. These are raw discard reads; do not wait
        // for DRDY or consume any of the values.
        RNG->SR &= ~RNG_SR_SEIS;
        for (unsigned int i = 0; i < 12; i++) {
            (void)RNG->DR;
        }

        // SEIS must remain clear after flushing. If it is set again, retry
        // recovery within the remaining budget before reporting failure.
        if (!(RNG->SR & RNG_SR_SEIS)) {
            return true;
        }
    }
    return false;
}

void rng_setup(void) {
    // Enable the peripheral clock even if an earlier boot stage left RNGEN set.
    __HAL_RCC_RNG_CLK_ENABLE();

    // Restart the generator at image startup.
    RNG->CR &= ~RNG_CR_RNGEN;
    RNG->CR |= RNG_CR_RNGEN;

    RNG->SR &= ~RNG_SR_CEIS;
    uint32_t recovery_attempts = 0;
    // Persistent seed errors leave the RNG output untrustworthy. Stop if
    // the startup recovery budget is exhausted.
    if (!rng_recover_seed_error(&recovery_attempts)) {
        rng_fatal_error();
    }

    // Always sample twice, even if an earlier boot stage enabled the
    // peripheral, so each image verifies the source before using it.
    uint32_t sample;
    if (!rng_try_sample(&sample) || !rng_try_sample(&sample)) {
        rng_fatal_error();
    }
}

bool rng_try_sample(uint32_t* result) {
    static uint32_t last_rng_result = 0;

    if (result == NULL) {
        return false;
    }
    const uint32_t seed_error_mask = RNG_SR_SECS | RNG_SR_SEIS;
    uint32_t recovery_attempts = 0;

    for (uint32_t attempt = 0; attempt < RNG_MAX_POLL_ATTEMPTS; attempt++) {
        uint32_t status = RNG->SR;
        // Clock errors do not invalidate available data (RM0433 section
        // 34.3.7). Clear CEIS; CECS clears in hardware when the clock recovers.
        if (status & RNG_SR_CEIS) {
            RNG->SR &= ~RNG_SR_CEIS;
        }
        if (status & seed_error_mask) {
            if (!rng_recover_seed_error(&recovery_attempts)) {
                return false;
            }
            continue;
        }

        if (!(status & RNG_SR_DRDY)) {
            continue;
        }

        // Get the new number
        uint32_t rv = RNG->DR;

        // Recheck status for errors that arrived during the data read.
        status = RNG->SR;
        if (status & RNG_SR_CEIS) {
            RNG->SR &= ~RNG_SR_CEIS;
        }

        // On STM32H753, zero from RNG_DR indicates invalid data and can signal
        // a late seed error (RM0433 section 34.7.3). Discard the sample and
        // recover on either indication, sharing the same per-call budget.
        if (rv == 0 || (status & seed_error_mask)) {
            if (!rng_recover_seed_error(&recovery_attempts)) {
                return false;
            }
            continue;
        }

        // Never return the same value twice in succession.
        if (rv != last_rng_result) {
            last_rng_result = rv;
            *result = rv;

            return true;
        }

        // A duplicate may be transient. Keep trying within the same
        // polling limit; a stuck source will exhaust it and fail closed.
    }

    return false;
}

uint32_t rng_sample(void) {
    uint32_t result;
    if (!rng_try_sample(&result)) {
        rng_fatal_error();
    }
    return result;
}

void rng_buffer(uint8_t* result, int len) {
    while (len > 0) {
        uint32_t sample = rng_sample();

        memcpy(result, &sample, MIN(4, len));

        len -= 4;
        result += 4;
    }
}

// EOF
