// SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
// SPDX-License-Identifier: GPL-3.0-or-later
//
// SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
// SPDX-License-Identifier: GPL-3.0-only
//
// (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
// and is covered by GPLv3 license found in COPYING.
//
//
// printf.c -- retarget STDOUT to USART console
//

#include <stdint.h>
#include <stdio.h>

#include "ui.h"

#include "stm32h7xx_hal.h"
#include "stm32h7xx_hal_uart.h"
#include "stm32h7xx_hal_uart_ex.h"

#include "printf.h"

UART_HandleTypeDef huart2;

void init_console_uart(void) {
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_USART2_CLK_ENABLE();

    GPIO_InitTypeDef GPIO_InitStruct = {0};
    GPIO_InitStruct.Pin              = GPIO_PIN_2;
    GPIO_InitStruct.Mode             = GPIO_MODE_AF_PP;
    GPIO_InitStruct.Alternate        = GPIO_AF7_USART2;
    GPIO_InitStruct.Speed            = GPIO_SPEED_HIGH;
    GPIO_InitStruct.Pull             = GPIO_NOPULL;
    HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

    GPIO_InitStruct.Pin  = GPIO_PIN_3;
    GPIO_InitStruct.Mode = GPIO_MODE_AF_OD;
    HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

    RCC_PeriphCLKInitTypeDef RCC_PeriphClkInit = {0};
    // Configure USART1/6 and USART2/3/4/5/7/8 clock sources
    RCC_PeriphClkInit.PeriphClockSelection      = RCC_PERIPHCLK_USART16 | RCC_PERIPHCLK_USART234578;
    RCC_PeriphClkInit.Usart16ClockSelection     = RCC_USART16CLKSOURCE_D2PCLK2;
    RCC_PeriphClkInit.Usart234578ClockSelection = RCC_USART234578CLKSOURCE_D2PCLK1;
    if (HAL_RCCEx_PeriphCLKConfig(&RCC_PeriphClkInit) != HAL_OK) {
        ui_show_fatal_error("Can't configure UART clock source");
    }

    huart2.Instance                    = USART2;
    huart2.Init.BaudRate               = 115200;
    huart2.Init.WordLength             = UART_WORDLENGTH_8B;
    huart2.Init.StopBits               = UART_STOPBITS_1;
    huart2.Init.Parity                 = UART_PARITY_NONE;
    huart2.Init.Mode                   = UART_MODE_TX_RX;
    huart2.Init.HwFlowCtl              = UART_HWCONTROL_NONE;
    huart2.Init.OverSampling           = UART_OVERSAMPLING_16;
    huart2.Init.OneBitSampling         = UART_ONE_BIT_SAMPLE_DISABLE;
    huart2.Init.ClockPrescaler         = UART_PRESCALER_DIV1;
    huart2.AdvancedInit.AdvFeatureInit = UART_ADVFEATURE_NO_INIT;
    if (HAL_UART_Init(&huart2) != HAL_OK) {
        ui_show_fatal_error("Can't configure USART2 clock source");
    }
}

int _write(int file, char* ptr, int len) {
    (void)file;

    if (HAL_UART_Transmit(&huart2, (uint8_t*)ptr, len, 1000) != HAL_OK) {
        return -1;
    }

    return len;
}
