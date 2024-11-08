// SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundation.xyz>
// SPDX-License-Identifier: GPL-3.0-or-later

#include <stdio.h>

#include "stm32h7xx_hal.h"

#include "adc.h"
#include "backlight.h"
#include "display.h"
#include "camera-ovm7690.h"
#include "frequency.h"
#include "gpio.h"
#include "se.h"

#ifndef PASSPORT_DEBUG_STACK
#define PASSPORT_DEBUG_STACK 0
#endif

#if PASSPORT_DEBUG_STACK
#include "utils.h"
#endif

void Passport_board_init(void) {
    /* Enable the console UART */
    frequency_update_console_uart();
    printf("[%s]\n", __func__);
    printf("%lu, %lu, %lu, %lu, %lu\n", HAL_RCC_GetSysClockFreq(), SystemCoreClock, HAL_RCC_GetHCLKFreq(),
           HAL_RCC_GetPCLK1Freq(), HAL_RCC_GetPCLK2Freq());

#if PASSPORT_DEBUG_STACK
    set_stack_sentinel();
#endif

    gpio_init();
    frequency_turbo(true);
    display_init(false);
    camera_init();
    adc_init();
    se_setup();

#if PASSPORT_DEBUG_STACK
    check_stack("Passport_board_init() complete", true);
#endif
}

void Passport_board_early_init(void) {}
