// SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//
// SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
// SPDX-License-Identifier: GPL-3.0-only
//
/*
 * (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
 * and is covered by GPLv3 license found in COPYING.
 *
 * sflash.c -- talk to the serial flash
 *
 */

#include <string.h>
#include <stdbool.h>
#include <stdio.h>

#include "spiflash.h"

// Connections:
// - SPI4 port
// - all port E
//
// SF_CS   => PE11
// SF_SCLK => PE12
// SF_MISO => PE13
// SF_MOSI => PE14

#define SF_CS_PIN GPIO_PIN_11    // port E
#define SF_SPI_SCK GPIO_PIN_12   // port E
#define SF_SPI_MISO GPIO_PIN_13  // port E
#define SF_SPI_MOSI GPIO_PIN_14  // port E

#define CMD_WRSR 0x01
#define CMD_WRITE 0x02
#define CMD_READ 0x03
#define CMD_FAST_READ 0x0b
#define CMD_RDSR 0x05
#define CMD_WREN 0x06
#define CMD_SEC_ERASE 0x20
#define CMD_RDCR 0x35
#define CMD_RD_DEVID 0x9f
#define CMD_CHIP_ERASE 0xc7
#define CMD_SECTOR_ERASE 0x20

// active-low chip-select line
#define CS_LOW() HAL_GPIO_WritePin(GPIOE, SF_CS_PIN, 0)
#define CS_HIGH() HAL_GPIO_WritePin(GPIOE, SF_CS_PIN, 1)

static SPI_HandleTypeDef sf_spi_port;

static HAL_StatusTypeDef wait_wip_done() {
    // read RDSR (status register) and busy-wait until
    // the write operation is done
    while (1) {
        uint8_t pkt = CMD_RDSR, stat = 0;

        CS_LOW();

        HAL_StatusTypeDef rv = HAL_SPI_Transmit(&sf_spi_port, &pkt, 1, HAL_MAX_DELAY);

        if (rv == HAL_OK) {
            rv = HAL_SPI_Receive(&sf_spi_port, &stat, 1, HAL_MAX_DELAY);
        }

        CS_HIGH();

        if (rv != HAL_OK) return rv;

        if (stat & 0x01) continue;

        return HAL_OK;
    }
}

static HAL_StatusTypeDef write_enable(void) {
    uint8_t pkt = CMD_WREN;

    CS_LOW();

    HAL_StatusTypeDef rv = HAL_SPI_Transmit(&sf_spi_port, &pkt, 1, HAL_MAX_DELAY);

    CS_HIGH();

    return rv;
}

HAL_StatusTypeDef spi_read_impl(uint32_t addr, int len, uint8_t* buf) {
    // send via SPI(1)
    uint8_t pkt[5] = {CMD_FAST_READ, (addr >> 16) & 0xff, (addr >> 8) & 0xff, addr & 0xff, 0x0};  // for fast-read case

    CS_LOW();

    HAL_StatusTypeDef rv = HAL_SPI_Transmit(&sf_spi_port, pkt, sizeof(pkt), HAL_MAX_DELAY);
    if (rv == HAL_OK) {
        rv = HAL_SPI_Receive(&sf_spi_port, (uint8_t*)buf, len, HAL_MAX_DELAY);
    }

    CS_HIGH();

    return rv;
}

#define NUM_BUFS_TO_COMPARE 3
#define MAX_SPI_REPEATED_READ_LEN 1024
#define MAX_READ_ATTEMPTS 9

HAL_StatusTypeDef spi_read(uint32_t addr, int len, uint8_t* buf) {
    uint8_t temp_bufs[NUM_BUFS_TO_COMPARE][MAX_SPI_REPEATED_READ_LEN];
    if (len > MAX_SPI_REPEATED_READ_LEN) {
        return spi_read_impl(addr, len, buf);
    }

    // Repeated read to mitigate SPI read errors
    uint32_t num_reads      = 0;
    uint32_t curr_idx       = 0;
    bool     all_bufs_equal = false;
    do {
        HAL_StatusTypeDef rv;
    retry:
        rv = spi_read_impl(addr, len, temp_bufs[curr_idx]);
        if (rv != HAL_OK) {
            printf("spi_read_impl() error: rv=%d\r\n", rv);
            return rv;
        }

        // Next index, plus wrap around
        curr_idx = (curr_idx + 1) % NUM_BUFS_TO_COMPARE;
        num_reads++;

        // Compare the buffers, but only after we've read the minimum number of times
        if (num_reads >= NUM_BUFS_TO_COMPARE) {
            all_bufs_equal = false;  // Assume they are all equal
            for (uint32_t i = 0; i < NUM_BUFS_TO_COMPARE - 1; i++) {
                if (memcmp(temp_bufs[i], temp_bufs[i + 1], len) != 0) {
                    printf("Buffers not equal! Rereading: addr=%lu, len=%d, num_reads=%lu\r\n", addr, len, num_reads);
                    goto retry;
                }
            }
            all_bufs_equal = true;
        }
    } while (!all_bufs_equal && (num_reads < MAX_READ_ATTEMPTS));

    // Copy data out to caller's buffer
    memcpy(buf, temp_bufs[0], len);
    return HAL_OK;
}

// Supports only up to SPI_FLASH_PAGE_SIZE bytes writes
HAL_StatusTypeDef spi_write(uint32_t addr, int len, const uint8_t* buf) {
    // enable writing
    HAL_StatusTypeDef rv = write_enable();
    if (rv) return rv;

    // do a "PAGE Program" aka. write
    uint8_t pkt[4] = {CMD_WRITE, (addr >> 16) & 0xff, (addr >> 8) & 0xff, addr & 0xff};

    CS_LOW();

    rv = HAL_SPI_Transmit(&sf_spi_port, pkt, sizeof(pkt), HAL_MAX_DELAY);
    if (rv == HAL_OK) {
        rv = HAL_SPI_Transmit(&sf_spi_port, (uint8_t*)buf, len, HAL_MAX_DELAY);
    }

    CS_HIGH();

    if (rv == HAL_OK) {
        rv = wait_wip_done();
    }

    return rv;
}

HAL_StatusTypeDef spi_setup(void) {
    // enable some internal clocks
    __HAL_RCC_GPIOE_CLK_ENABLE();
    __HAL_RCC_SPI4_CLK_ENABLE();

    // simple pins
    GPIO_InitTypeDef setup = {
        .Pin       = SF_CS_PIN,
        .Mode      = GPIO_MODE_OUTPUT_PP,
        .Pull      = GPIO_NOPULL,
        .Speed     = GPIO_SPEED_FREQ_MEDIUM,
        .Alternate = 0,
    };
    HAL_GPIO_Init(GPIOE, &setup);

    // starting value: high
    HAL_GPIO_WritePin(GPIOE, SF_CS_PIN, 1);

    // SPI pins, on various ports
    setup.Pin       = SF_SPI_SCK;
    setup.Mode      = GPIO_MODE_AF_PP;
    setup.Alternate = GPIO_AF5_SPI4;
    HAL_GPIO_Init(GPIOE, &setup);

    setup.Pin = SF_SPI_MOSI | SF_SPI_MISO;
    HAL_GPIO_Init(GPIOE, &setup);

    memset(&sf_spi_port, 0, sizeof(sf_spi_port));

    sf_spi_port.Instance = SPI4;

    // see SPI_InitTypeDef
    sf_spi_port.Init.Mode              = SPI_MODE_MASTER;
    sf_spi_port.Init.Direction         = SPI_DIRECTION_2LINES;
    sf_spi_port.Init.DataSize          = SPI_DATASIZE_8BIT;
    sf_spi_port.Init.CLKPolarity       = SPI_POLARITY_LOW;
    sf_spi_port.Init.CLKPhase          = SPI_PHASE_1EDGE;
    sf_spi_port.Init.NSS               = SPI_NSS_SOFT;
    sf_spi_port.Init.BaudRatePrescaler = SPI_BAUDRATEPRESCALER_16;  // conservative
    sf_spi_port.Init.FirstBit          = SPI_FIRSTBIT_MSB;
    sf_spi_port.Init.TIMode            = SPI_TIMODE_DISABLED;
    sf_spi_port.Init.CRCCalculation    = SPI_CRCCALCULATION_DISABLED;

    return HAL_SPI_Init(&sf_spi_port);
}

HAL_StatusTypeDef spi_flash_deinit(void) {
    __HAL_RCC_SPI4_CLK_DISABLE();

    HAL_GPIO_DeInit(GPIOE, SF_CS_PIN);
    HAL_GPIO_DeInit(GPIOE, SF_SPI_SCK);
    HAL_GPIO_DeInit(GPIOE, SF_SPI_MOSI);
    HAL_GPIO_DeInit(GPIOE, SF_SPI_MISO);

    return HAL_SPI_DeInit(&sf_spi_port);
}

HAL_StatusTypeDef spi_read_id(uint32_t* id_out) {
    uint8_t pkt[4] = {CMD_RD_DEVID, 0x00, 0x00, 0x00};

    CS_LOW();

    HAL_StatusTypeDef rv = HAL_SPI_TransmitReceive(&sf_spi_port, (uint8_t*)&pkt, (uint8_t*)&pkt, 4, HAL_MAX_DELAY);

    *id_out = (pkt[1] << 16) | (pkt[2] << 8) | pkt[3];

    CS_HIGH();

    return rv;
}

HAL_StatusTypeDef spi_chip_erase(void) {
    // enable writing
    HAL_StatusTypeDef rv = write_enable();
    if (rv) return rv;

    uint8_t pkt[1] = {CMD_CHIP_ERASE};

    CS_LOW();
    rv = HAL_SPI_Transmit(&sf_spi_port, (uint8_t*)&pkt, sizeof(pkt), HAL_MAX_DELAY);
    CS_HIGH();

    return rv;
}

HAL_StatusTypeDef spi_is_busy(bool* busy) {
    uint8_t pkt[2] = {CMD_RDSR, 0x00};

    CS_LOW();
    HAL_StatusTypeDef rv =
        HAL_SPI_TransmitReceive(&sf_spi_port, (uint8_t*)&pkt, (uint8_t*)&pkt, sizeof(pkt), HAL_MAX_DELAY);
    CS_HIGH();

    *busy = pkt[1] & 0x01;  // S0 "busy" bit

    return rv;
}

HAL_StatusTypeDef spi_sector_erase(uint32_t addr) {
    // enable writing
    HAL_StatusTypeDef rv = write_enable();
    if (rv) return rv;

    uint8_t pkt[4] = {CMD_SECTOR_ERASE, (addr >> 16) & 0xff, (addr >> 8) & 0xff, addr & 0xff};

    CS_LOW();
    rv = HAL_SPI_Transmit(&sf_spi_port, (uint8_t*)&pkt, sizeof(pkt), HAL_MAX_DELAY);
    CS_HIGH();

    if (rv == HAL_OK) {
        rv = wait_wip_done();
    }

    return rv;
}
