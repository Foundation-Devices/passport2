// SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
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
#include "utils.h"

void Passport_board_init(void) {
    /* Enable the console UART */
    frequency_update_console_uart();
    printf("[%s]\n", __func__);
    printf("%lu, %lu, %lu, %lu, %lu\n", HAL_RCC_GetSysClockFreq(), SystemCoreClock, HAL_RCC_GetHCLKFreq(),
           HAL_RCC_GetPCLK1Freq(), HAL_RCC_GetPCLK2Freq());

    set_stack_sentinel();

    gpio_init();
    frequency_turbo(true);
    display_init(false);
    camera_init();
    adc_init();
    se_setup();

    // check_stack("Passport_board_init() complete", true);
}

void Passport_board_early_init(void) {}
