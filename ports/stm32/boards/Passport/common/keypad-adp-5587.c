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

#ifndef PASSPORT_BOOTLOADER
    // Enable GPIO interrupt
    rc = keypad_write(KBD_ADDR, KBD_REG_GPIO_INT_EN1, 0xFF);
    if (rc < 0) return -1;

    rc = keypad_write(KBD_ADDR, KBD_REG_GPIO_INT_EN2, 0xFF);
    if (rc < 0) return -1;

    rc = keypad_write(KBD_ADDR, KBD_REG_GPIO_INT_EN3, 0x03);
    if (rc < 0) return -1;

    // Setup the configuration register
    rc = keypad_write(KBD_ADDR, KBD_REG_CFG, KBD_REG_CFG_INT_CFG | KBD_REG_CFG_GPI_IEN | KBD_REG_CFG_KE_IEN);
    if (rc < 0) return -1;
#endif /* PASSPORT_BOOTLOADER */

    // Enable GPI part of event FIFO (R0 to R7, C0 to C7, C8 to C9)
    rc = keypad_write(KBD_ADDR, KBD_REG_GPI_EM_REG1, 0xFF);
    if (rc < 0) return -1;

    rc = keypad_write(KBD_ADDR, KBD_REG_GPI_EM_REG2, 0xFF);
    if (rc < 0) return -1;

    rc = keypad_write(KBD_ADDR, KBD_REG_GPI_EM_REG3, 0x03);
    if (rc < 0) return -1;
    return 0;
}

#ifndef PASSPORT_BOOTLOADER
void keypad_ISR(void) {
    int     rc;
    uint8_t key        = 0;
    uint8_t key_count  = 0;
    uint8_t loop_count = 0;

    while (loop_count < 10) {
        rc = keypad_read(KBD_ADDR, KBD_REG_KEY_EVENTA, &key, 1);
        if (rc < 0) {
#ifndef PASSPORT_BOOTLOADER
            // printf("keypad_ISR() read error\n");
#endif /* PASSPORT_BOOTLOADER */
            break;
        }

        if (key == 0) {
            // printf("keypad_ISR() no key in queue\n");
            break;
        }

        ring_buffer_enqueue(key);
        key_count++;
        loop_count++;
    }

    if (key_count) {
        /* Clear the interrupt on the keypad controller */
        rc = keypad_write(KBD_ADDR, KBD_REG_INT_STAT, 0xFF);
        if (rc < 0) {
            // printf("[%s] I2C problem\n", __func__);
        }
    } else {
        /*
         * We're getting interrupts but no key codes...the keypad
         * controller is in a strange state. We'll reset it and reconfigure
         * it to get it working again.
         */
        keypad_reset();
        keypad_setup();
    }
}
#endif /* PASSPORT_BOOTLOADER */

void keypad_init(void) {
    int              rcc;
    GPIO_InitTypeDef GPIO_InitStruct = {0};

    __HAL_RCC_GPIOE_CLK_ENABLE();

    GPIO_InitStruct.Pin   = GPIO_PIN_2;
    GPIO_InitStruct.Mode  = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull  = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(GPIOE, &GPIO_InitStruct);

#ifndef PASSPORT_BOOTLOADER
    // Need to specify the size of the ring buffer 128 for a test
    ring_buffer_init();
#endif /* PASSPORT_BOOTLOADER */

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

/**
 * Reads number of keys in the key queue.
 */
static bool read_num_keys(uint8_t *num_keys) {
    uint8_t data = 0;

    if (!num_keys) {
        return false;
    }

    int rc = keypad_read(KBD_ADDR, KBD_REG_KEY_LCK_EC_STAT, &data, 1);
    if (rc < 0) {
        return false;
    }

    *num_keys = data & 0x0f; // Use lower 4 bits

    return true;
}

bool keypad_poll_key(uint8_t* key) {
    if (!key) {
        return false;
    }

    // A delay to not overwhelm the keypad chip to avoid its lockup
    delay_ms(100);

    // Only read from the key queue if it's not empty
    uint8_t num_keys = 0;
    if (read_num_keys(&num_keys) && num_keys) {
        return false;
    }

    // Read from the key queue
    int rc = keypad_read(KBD_ADDR, KBD_REG_KEY_EVENTA, key, 1);
    if (rc < 0) {
        return false;
    }

    return true;
}
