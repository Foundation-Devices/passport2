// SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//
// EEPROM driver for Passport Gen 1.2

#ifndef __EEPROM_H__
#define __EEPROM_H__

#include "stm32h7xx_hal.h"
#include "utils.h"
#include "i2c-init.h"

static const uint8_t CAT24C_ADDR = 0x50 << 1;
static const uint8_t PAGE_SIZE   = 0x10;

HAL_StatusTypeDef eeprom_init(I2C_HandleTypeDef* handle);
HAL_StatusTypeDef eeprom_read(uint16_t offset, uint8_t* buffer, uint8_t len);
HAL_StatusTypeDef eeprom_write(uint16_t offset, uint8_t* buffer, uint8_t len);

int32_t eeprom_get_rtc_calibration_offset(int32_t _default);
bool    eeprom_set_rtc_calibration_offset(int32_t offset);

uint16_t eeprom_get_screen_brightness(uint16_t _default);
bool     eeprom_set_screen_brightness(uint16_t brightness);

#define EEPROM_EMPTY_TIMESTAMP (0xFFFFFFFF)

#endif /* __EEPROM_H__ */