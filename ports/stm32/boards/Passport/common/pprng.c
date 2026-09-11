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

void rng_setup(void) {
    // Enable the peripheral clock even if an earlier boot stage left RNGEN set.
    __HAL_RCC_RNG_CLK_ENABLE();

    // Restart the generator at image startup.
    RNG->CR &= ~RNG_CR_RNGEN;
    RNG->CR |= RNG_CR_RNGEN;

    // Clear latched errors and flush the pipeline using ST's seed-error
    // recovery sequence (RM0433 section 34.3.7). These are raw discard reads,
    // not samples: do not wait for DRDY or consume any of the values.
    RNG->SR &= ~(RNG_SR_SEIS | RNG_SR_CEIS);
    for (unsigned int i = 0; i < 12; i++) {
        (void)RNG->DR;
    }
    // SEIS must remain clear after flushing the pipeline. If it is set again,
    // recovery failed and the RNG output cannot be trusted; stop execution.
    if (RNG->SR & RNG_SR_SEIS) {
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
    const uint32_t error_mask = RNG_SR_SECS | RNG_SR_CECS | RNG_SR_SEIS | RNG_SR_CEIS;

    for (uint32_t attempt = 0; attempt < RNG_MAX_POLL_ATTEMPTS; attempt++) {
        // Check both current error status and latched error flags. A flagged
        // sample is a hard failure; callers must not silently degrade.
        uint32_t status = RNG->SR;
        if (status & error_mask) {
            return false;
        }

        if (!(status & RNG_SR_DRDY)) {
            continue;
        }

        // Get the new number
        uint32_t rv = RNG->DR;

        // Catch an error that arrived between the status check and the data
        // read. The value must not be used in that case.
        if (RNG->SR & error_mask) {
            return false;
        }

        // On STM32H753, zero from RNG_DR indicates invalid data and can signal
        // a late seed error (RM0433 section 34.7.3). Reject it on every read,
        // and never return the same value twice in succession.
        if (rv != 0 && rv != last_rng_result) {
            last_rng_result = rv;
            *result = rv;

            return true;
        }

        // A zero or duplicate may be transient. Keep trying within the same
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
