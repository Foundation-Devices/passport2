/*
 * SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundation.xyz>
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#ifndef _SPIFLASH_H_
#define _SPIFLASH_H_

#include <stdbool.h>

#include "../stm32h7xx_hal_conf.h"

#define WINBOND_FLASH_ID_1 0xEF4014
#define WINBOND_FLASH_ID_2 0xEF4017

#define SPI_FLASH_PAGE_SIZE (256)
#define SPI_FLASH_SECTOR_SIZE (4096) // 4K

extern HAL_StatusTypeDef spi_setup(void);
extern HAL_StatusTypeDef spi_flash_deinit(void);
extern HAL_StatusTypeDef spi_write(uint32_t addr, int len, const uint8_t* buf);
extern HAL_StatusTypeDef spi_read(uint32_t addr, int len, uint8_t* buf);
extern HAL_StatusTypeDef spi_sector_erase(uint32_t addr);
extern HAL_StatusTypeDef spi_read_id(uint32_t *id_out);
extern HAL_StatusTypeDef spi_chip_erase(void);
extern HAL_StatusTypeDef spi_is_busy(bool* busy);

bool spi_get_scv_key(uint8_t* buf);
bool spi_set_scv_key(uint8_t* buf);
bool spi_clear_scv_key();

#endif /* _SPIFLASH_H_ */
