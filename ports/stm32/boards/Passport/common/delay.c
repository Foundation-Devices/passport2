// SPDX-FileCopyrightText: 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//
// SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
// SPDX-License-Identifier: GPL-3.0-only
//
/*
 * (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
 * and is covered by GPLv3 license found in COPYING.
 *
 * delay.c -- Software delay loops (we have no interrupts)
 *
 */
#include "stm32h7xx_hal.h"

#include "delay.h"

void delay_ms(int ms) {
    uint32_t start_tick = HAL_GetTick();

    uint32_t curr_tick;
    do {
        curr_tick = HAL_GetTick();
    } while (curr_tick - start_tick < ms);
}

void delay_us(int us) {
    if (us > 1000) {
        delay_ms((us + 500) / 1000);
    } else {
        const uint32_t ucount = SystemCoreClock / 2000000 * us / 2;
        for (uint32_t count = 0; ++count <= ucount;) {
        }
    }
}
