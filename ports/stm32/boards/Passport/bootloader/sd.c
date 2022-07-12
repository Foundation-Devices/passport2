// SPDX-FileCopyrightText: 2022 Foundation Devices, Inc.
// <hello@foundationdevices.com> SPDX-License-Identifier: GPL-3.0-or-later
//
// sd.c - SD card routines

#include "sd.h"

#include <stdio.h>
#include <assert.h>

static SD_HandleTypeDef hsd;

HAL_StatusTypeDef sd_init(void) {
    HAL_StatusTypeDef res;
    GPIO_InitTypeDef  GPIO_InitStruct = {0};

    // Init SD card detect pin
    __HAL_RCC_GPIOE_CLK_ENABLE();
    GPIO_InitStruct.Pin  = GPIO_PIN_3;
    GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    HAL_GPIO_Init(GPIOE, &GPIO_InitStruct);

    // Init SDIO
    RCC_PeriphCLKInitTypeDef PeriphClkInitStruct = {0};
    PeriphClkInitStruct.PeriphClockSelection     = RCC_PERIPHCLK_SDMMC;
    PeriphClkInitStruct.SdmmcClockSelection      = RCC_SDMMCCLKSOURCE_PLL;
    if ((res = HAL_RCCEx_PeriphCLKConfig(&PeriphClkInitStruct)) != HAL_OK) {
        return res;
    }

    __HAL_RCC_SDMMC1_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();
    __HAL_RCC_GPIOD_CLK_ENABLE();

    // Reset SDMMC
    __HAL_RCC_SDMMC1_FORCE_RESET();
    __HAL_RCC_SDMMC1_RELEASE_RESET();

    GPIO_InitStruct.Pin       = GPIO_PIN_8 | GPIO_PIN_9 | GPIO_PIN_10 | GPIO_PIN_11 | GPIO_PIN_12;
    GPIO_InitStruct.Mode      = GPIO_MODE_AF_PP;
    GPIO_InitStruct.Pull      = GPIO_NOPULL;
    GPIO_InitStruct.Speed     = GPIO_SPEED_FREQ_VERY_HIGH;
    GPIO_InitStruct.Alternate = GPIO_AF12_SDIO1;
    HAL_GPIO_Init(GPIOC, &GPIO_InitStruct);

    GPIO_InitStruct.Pin       = GPIO_PIN_2;
    GPIO_InitStruct.Mode      = GPIO_MODE_AF_PP;
    GPIO_InitStruct.Pull      = GPIO_NOPULL;
    GPIO_InitStruct.Speed     = GPIO_SPEED_FREQ_VERY_HIGH;
    GPIO_InitStruct.Alternate = GPIO_AF12_SDIO1;
    HAL_GPIO_Init(GPIOD, &GPIO_InitStruct);

    hsd.Instance                 = SDMMC1;
    hsd.Init.ClockEdge           = SDMMC_CLOCK_EDGE_RISING;
    hsd.Init.ClockPowerSave      = SDMMC_CLOCK_POWER_SAVE_ENABLE;
    hsd.Init.BusWide             = SDMMC_BUS_WIDE_4B;
    hsd.Init.HardwareFlowControl = SDMMC_HARDWARE_FLOW_CONTROL_DISABLE;
    hsd.Init.ClockDiv            = SDMMC_NSpeed_CLK_DIV;

    return HAL_SD_Init(&hsd);
}

HAL_StatusTypeDef sd_card_init(void) {
    return HAL_SD_InitCard(&hsd);
}

bool is_sd_card_present(void) {
    // An empty SD card slot has a "card detect" pin pulled up.
    // It's pulled down when an SD card is inserted
    if (HAL_GPIO_ReadPin(GPIOE, GPIO_PIN_3)) {
        return false;
    }

    return true;
}

HAL_StatusTypeDef sd_read_block(uint32_t addr, size_t len, uint8_t* buf) {
    HAL_StatusTypeDef res;
    // NOTE: We allocate 9 blocks of 512 bytes - 8 for the max size to read, and an extra one in case the address
    //       given is not a multiple of 512.  Then we round the address down, and read more data than necessary,
    //       and when doing the memcpy() below, we adjust for the source address.
    uint8_t  block_buf[9 * SD_BLOCK_SIZE_BYTES] = {0};
    uint32_t addr_offset                        = (addr % SD_BLOCK_SIZE_BYTES);
    uint32_t start_read_block_addr              = (addr - addr_offset) / SD_BLOCK_SIZE_BYTES;
    uint32_t read_len = len + (((addr_offset + SD_BLOCK_SIZE_BYTES - 1) / SD_BLOCK_SIZE_BYTES) * SD_BLOCK_SIZE_BYTES);
    uint32_t read_blocks = (read_len + SD_BLOCK_SIZE_BYTES - 1) / SD_BLOCK_SIZE_BYTES;

// #define DEBUG_PRINT_SD_READ_BLOCK
#ifdef DEBUG_PRINT_SD_READ_BLOCK
    printf("addr=0x%08lx\r\n", addr);
    printf("len=%u\r\n", len);
    printf("start_read_block_addr=0x%08lx\r\n", start_read_block_addr);
    printf("addr_offset=0x%08lx\r\n", addr_offset);
    printf("read_len=%lu\r\n", read_len);
    printf("read_blocks=%lu\r\n", read_blocks);
#endif
    // printf("len=%u\r\n", len);
    // printf("num_blocks=%lu\r\n", num_blocks);
    assert(sizeof(block_buf) % SD_BLOCK_SIZE_BYTES == 0);
    assert(read_blocks <= sizeof(block_buf) / SD_BLOCK_SIZE_BYTES);

    if ((res = HAL_SD_ReadBlocks(&hsd, (uint8_t*)&block_buf, start_read_block_addr, read_blocks, HAL_MAX_DELAY)) !=
        HAL_OK) {
        // printf("HAL_SD_ReadBlocks(%d) failed: %d\r\n", (unsigned int)start_read_block_addr, (unsigned int)res);
        return res;
    }

    memcpy(buf, block_buf + addr_offset, len);

    // printf("sd_read_block() done!\r\n");
    return HAL_OK;
}
