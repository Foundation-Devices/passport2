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

#define RNG_TIMEOUT_MS 10U

static bool rng_cycle_counter_setup(void) {
    if (DWT->CTRL & DWT_CTRL_CYCCNTENA_Msk) {
        return true;
    }

    CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
    DWT->LAR = 0xc5acce55;
    DWT->CYCCNT = 0;
    DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;

    return (DWT->CTRL & DWT_CTRL_CYCCNTENA_Msk) != 0;
}

void rng_setup(void) {
    // Enable the peripheral clock even if an earlier boot stage left RNGEN set.
    __HAL_RCC_RNG_CLK_ENABLE();

    // Start each image from a known peripheral state. Clearing the latched
    // interrupt flags and restarting the generator is the recovery sequence
    // recommended by ST after a seed error. A persistent current error is
    // still caught by rng_try_sample() below and fails closed.
    RNG->SR &= ~(RNG_SR_SEIS | RNG_SR_CEIS);
    RNG->CR &= ~RNG_CR_RNGEN;
    RNG->CR |= RNG_CR_RNGEN;

    // Always sample twice, even if an earlier boot stage enabled the
    // peripheral, so each image verifies the source before using it.
    uint32_t sample;
    if (!rng_try_sample(&sample) || !rng_try_sample(&sample)) {
        rng_fatal_error();
    }
}

bool rng_try_sample(uint32_t* result) {
    static uint32_t last_rng_result;
    static bool     have_last_rng_result;

    if (result == NULL) {
        return false;
    }
    if (!rng_cycle_counter_setup()) {
        return false;
    }

    const uint32_t error_mask = RNG_SR_SECS | RNG_SR_CECS | RNG_SR_SEIS | RNG_SR_CEIS;
    const uint32_t timeout_cycles = (SystemCoreClock / 1000U) * RNG_TIMEOUT_MS;
    const uint32_t start_cycle = DWT->CYCCNT;

    while ((DWT->CYCCNT - start_cycle) < timeout_cycles) {
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

        // Continuous test: never return the same value twice in succession.
        if (!have_last_rng_result || rv != last_rng_result) {
            last_rng_result = rv;
            have_last_rng_result = true;
            *result = rv;

            return true;
        }

        // A duplicate may be transient. Keep trying within the same bounded
        // interval; a stuck source will time out and fail closed.
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
