// SPDX-FileCopyrightText: 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//

#include <stdio.h>
#include <string.h>

#include "stm32h7xx_hal.h"
#include "stm32h7xx_hal_i2c_ex.h"
#include "stm32h7xx_hal_gpio.h"

I2C_HandleTypeDef g_hi2c2 = {.Instance = NULL};

void i2c_init() {
    HAL_StatusTypeDef rc;
    GPIO_InitTypeDef  GPIO_InitStruct;

    if (g_hi2c2.Instance == NULL) {
        memset(&GPIO_InitStruct, 0, sizeof(GPIO_InitStruct));
        GPIO_InitStruct.Pin       = GPIO_PIN_10 | GPIO_PIN_11;
        GPIO_InitStruct.Mode      = GPIO_MODE_AF_OD;
        GPIO_InitStruct.Pull      = GPIO_NOPULL;
        GPIO_InitStruct.Speed     = GPIO_SPEED_FREQ_LOW;
        GPIO_InitStruct.Alternate = GPIO_AF4_I2C2;
        HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);

        __HAL_RCC_I2C2_CLK_ENABLE();

        g_hi2c2.Instance    = I2C2;
        g_hi2c2.Init.Timing = 0x00B03FDB; /* 0x0010061A - 400 KHz @ 64 MHz */
                                          /* 0x00B03FDB - 400 KHz @ 480 MHz */
        g_hi2c2.Init.OwnAddress1      = 0;
        g_hi2c2.Init.AddressingMode   = I2C_ADDRESSINGMODE_7BIT;
        g_hi2c2.Init.DualAddressMode  = I2C_DUALADDRESS_DISABLE;
        g_hi2c2.Init.OwnAddress2      = 0;
        g_hi2c2.Init.OwnAddress2Masks = I2C_OA2_NOMASK;
        g_hi2c2.Init.GeneralCallMode  = I2C_GENERALCALL_DISABLE;
        g_hi2c2.Init.NoStretchMode    = I2C_NOSTRETCH_DISABLE;
        rc                            = HAL_I2C_Init(&g_hi2c2);
        if (rc != HAL_OK)
#ifdef PASSPORT_BOOTLOADER
            ;
#else
            // printf("[%s-%d] HAL_I2C_Init failed\n", __func__, __LINE__);
            ;
#endif /* PASSPORT_BOOTLOADER */
    }
}
