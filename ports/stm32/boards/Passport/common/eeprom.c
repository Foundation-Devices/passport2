// SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//
// EEPROM driver and accessor functions for Passport Gen 1.2

#include "eeprom.h"
#include "i2c-init.h"
#include <stdio.h>

static I2C_HandleTypeDef* hi2c = NULL;

HAL_StatusTypeDef eeprom_init(I2C_HandleTypeDef* handle) {
    i2c_init();
    hi2c = handle;
    return HAL_OK;
}

HAL_StatusTypeDef eeprom_read(uint16_t offset, uint8_t* buffer, uint8_t len) {
    uint8_t chip_addr_offset = (uint8_t)(offset >> 8);
    uint8_t addr_offset      = (uint8_t)(offset);

    // TODO: Need to add a loop for reads larger than a page size as done in eeprom_write() below.
    HAL_StatusTypeDef ret =
        HAL_I2C_Master_Transmit(hi2c, CAT24C_ADDR + (chip_addr_offset << 1), &addr_offset, 1, HAL_MAX_DELAY);

    if (ret != HAL_OK) {
        return ret;
    } else {
        ret = HAL_I2C_Master_Receive(hi2c, CAT24C_ADDR, buffer, len, HAL_MAX_DELAY);
        if (ret != HAL_OK) {
            return ret;
        }
    }

    return HAL_OK;
}

HAL_StatusTypeDef eeprom_write(uint16_t offset, uint8_t* buffer, uint8_t len) {
    HAL_StatusTypeDef ret;
    uint8_t           write_buf[17];

    if (len == 0) {
        return HAL_ERROR;
    }
    do {
        uint8_t chip_addr_offset = (uint8_t)(offset >> 8);
        write_buf[0]             = (uint8_t)offset;
        uint8_t len_to_write     = MIN(len, PAGE_SIZE);

        for (uint8_t i = 0; i < PAGE_SIZE; i++) {
            write_buf[i + 1] = buffer[i];
        }
        ret = HAL_I2C_Master_Transmit(hi2c, CAT24C_ADDR + (chip_addr_offset << 1), write_buf, len_to_write + 1,
                                      HAL_MAX_DELAY);
        if (ret != HAL_OK) {
            return ret;
        }
        HAL_Delay(5);  // Twr = 5ms. Write cycle time before new commands can be issued (Can cause faults if violated).

        offset += PAGE_SIZE;
        buffer += PAGE_SIZE;
        len -= len_to_write;
    } while (len > 0);

    return HAL_OK;
}

/*
 * =================
 * EEPROM Memory Map
 * =================
 * Address  Size  Name
 * -------  ----  ---------------------------------
 *      0      4  Reserved
 *      4      2  Screen brightness
 *
 */
#define EEPROM_ADDR_SCREEN_BRIGHTNESS 4

uint16_t eeprom_get_screen_brightness(uint16_t _default) {
    uint16_t brightness = 0;
    if (eeprom_read(EEPROM_ADDR_SCREEN_BRIGHTNESS, (uint8_t*)&brightness, sizeof(uint16_t)) == HAL_OK) {
        return brightness;
    }

    // Got an error on read, so return the default
    return _default;
}

bool eeprom_set_screen_brightness(uint16_t brightness) {
    return eeprom_write(EEPROM_ADDR_SCREEN_BRIGHTNESS, (uint8_t*)&brightness, sizeof(uint16_t)) == HAL_OK;
}
