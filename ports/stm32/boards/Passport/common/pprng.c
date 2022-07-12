// SPDX-FileCopyrightText: 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//
// SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
// SPDX-License-Identifier: GPL-3.0-only
//
/*
 * (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
 * and is covered by GPLv3 license found in COPYING.
 */
#include <string.h>

#include "stm32h7xx_hal_conf.h"

#include "delay.h"
#include "pprng.h"
#include "utils.h"

void rng_setup(void) {
    if (RNG->CR & RNG_CR_RNGEN) {
        // already setup
        return;
    }

    // Enable the RNG clock
    __HAL_RCC_RNG_CLK_ENABLE();

    // Enable the RNG
    RNG->CR |= RNG_CR_RNGEN;

    // Sample twice to be sure that we have a
    // valid RNG result.
    uint32_t chk  = rng_sample();
    uint32_t chk2 = rng_sample();

    // die if we are clearly not getting random values
    if (chk == 0 || chk == ~0 || chk2 == 0 || chk2 == ~0 || chk == chk2) {
        while (1)
            ;
    }
}

uint32_t rng_sample(void) {
    static uint32_t last_rng_result;

    while (1) {
        // Check if data register contains valid random data
        while (!(RNG->SR & RNG_SR_DRDY)) {
            // busy wait; okay to get stuck here... better than failing.
        }

        // Get the new number
        uint32_t rv = RNG->DR;

        if (rv != last_rng_result && rv) {
            last_rng_result = rv;

            return rv;
        }

        // keep trying if not a new number
    }

    // NOT-REACHED
}

void rng_buffer(uint8_t* result, int len) {
    while (len > 0) {
        uint32_t t = rng_sample();

        memcpy(result, &t, MIN(4, len));

        len -= 4;
        result += 4;
    }
}

// EOF
