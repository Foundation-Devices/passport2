// SPDX-FileCopyrightText: 2022 Foundation Devices, Inc.
// <hello@foundation.xyz> SPDX-License-Identifier: GPL-3.0-or-later
//
// sd.h - SD card routines

#ifndef _BOOTLOADER_SD_H_
#define _BOOTLOADER_SD_H_

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

#include "stm32h7xx_hal.h"

// This is fixed and shouldn't be changed
#define SD_BLOCK_SIZE_BYTES (512)

HAL_StatusTypeDef sd_init(void);
HAL_StatusTypeDef sd_card_init(void);
bool is_sd_card_present(void);
HAL_StatusTypeDef sd_read_block(uint32_t addr, size_t len, uint8_t* buf);

#endif // _BOOTLOADER_SD_H_
