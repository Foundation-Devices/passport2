// SPDX-FileCopyrightText: 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//

#include <stdio.h>
#include <string.h>
#include <stdbool.h>

#include "stm32h7xx_hal.h"

#include "delay.h"
#include "keypad-adp-5587.h"

#ifndef PASSPORT_BOOTLOADER
#include "extint.h"
#endif /* PASSPORT_BOOTLOADER */

static I2C_HandleTypeDef* hi2c = NULL;

static void keypad_reset(void) {
    volatile int i;

    // Toggle reset pin of keypad controller (pin PE2 on schematic)
    HAL_GPIO_WritePin(GPIOE, GPIO_PIN_2, 0);
    for (i = 0; i < 10; ++i)
        delay_us(1000);
    HAL_GPIO_WritePin(GPIOE, GPIO_PIN_2, 1);
    for (i = 0; i < 10; ++i)
        delay_us(1000);
}

static int keypad_setup(void) {
    int rc;

    // Enable GPI part of event FIFO (R0 to R7, C0 to C7, C8 to C9)
    rc = keypad_write(KBD_ADDR, KBD_REG_GPI_EM_REG1, 0xFF);
    if (rc < 0) return -1;

    rc = keypad_write(KBD_ADDR, KBD_REG_GPI_EM_REG2, 0xFF);
    if (rc < 0) return -1;

    rc = keypad_write(KBD_ADDR, KBD_REG_GPI_EM_REG3, 0x03);
    if (rc < 0) return -1;
    return 0;
}

void keypad_init(void) {
    int              rcc;
    GPIO_InitTypeDef GPIO_InitStruct = {0};

    __HAL_RCC_GPIOE_CLK_ENABLE();

    GPIO_InitStruct.Pin   = GPIO_PIN_2;
    GPIO_InitStruct.Mode  = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull  = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(GPIOE, &GPIO_InitStruct);

    i2c_init();
    hi2c = &g_hi2c2;

    keypad_reset();
    rcc = keypad_setup();
    if (rcc < 0)
#ifdef PASSPORT_BOOTLOADER
        ;
#else
        ;
        // printf("[%s-%d] keypad_setup() failed\n", __func__, __LINE__);
#endif /* PASSPORT_BOOTLOADER */
}

int keypad_write(uint8_t address, uint8_t reg, uint8_t data) {
    HAL_StatusTypeDef rc;
    rc = HAL_I2C_Mem_Write(hi2c, address, reg, I2C_MEMADD_SIZE_8BIT, &data, 1, 100);
    if (rc != HAL_OK) return -1;
    return 0;
}

int keypad_read(uint8_t address, uint8_t reg, uint8_t* data, uint8_t len) {
    HAL_StatusTypeDef rc;
    rc = HAL_I2C_Master_Transmit(hi2c, address, &reg, 1, 100);
    if (rc != HAL_OK)
        return -1;
    else {
        rc = HAL_I2C_Master_Receive(hi2c, address, data, len, 100);
        if (rc != HAL_OK) return -1;
    }
    return 0;
}

bool keypad_poll_key(uint8_t* key) {
    if (!key) {
        return false;
    }

    // A delay to not overwhelm the keypad chip to avoid its lockup
    delay_ms(50);

    int rc = keypad_read(KBD_ADDR, KBD_REG_KEY_EVENTA, key, 1);
    if (rc < 0) {
        return false;
    }

    return true;
}
