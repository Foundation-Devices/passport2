// SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//
// SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
// SPDX-License-Identifier: GPL-3.0-only
//
#include <errno.h>
#include <string.h>

#include <stdio.h>
#include "printf.h"

#include "../stm32h7xx_hal_conf.h"

#include "delay.h"
#include "fwheader.h"
#include "pprng.h"
#include "se.h"
#include "se-atecc608a.h"
#include "secrets.h"
#include "utils.h"

#include "flash.h"
#include "update.h"
#include "verify.h"
#include "spiflash.h"
#include "firmware-keys.h"

#include "backlight.h"
#include "display.h"
#include "keypad-adp-5587.h"
#include "gpio.h"
#include "hash.h"
#include "secresult.h"
#include "splash.h"
#include "ui.h"
#include "version_info.h"
#include "images.h"
#include "eeprom.h"
#include "sd.h"

#ifdef FACTORY_TEST
#include "factory-test.h"
#endif

// #define DEBUG_DUMP

/*
 * This is an empty function to satisfy the linker requirement for init
 * when the startup_stm32h753xx.s file was pulled into the bootloader
 * build to define the full vector table.
 */
void _init(void) {}

void SysTick_Handler(void) {
    HAL_IncTick();
}

static void SystemClock_Config(void) {
    HAL_StatusTypeDef        rc;
    RCC_ClkInitTypeDef       RCC_ClkInitStruct   = {0};
    RCC_OscInitTypeDef       RCC_OscInitStruct   = {0};
    RCC_PeriphCLKInitTypeDef PeriphClkInitStruct = {0};

    /*!< Supply configuration update enable */
    rc = HAL_PWREx_ConfigSupply(PWR_LDO_SUPPLY);
    if (rc != HAL_OK) return;

    __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE1);

    while (!__HAL_PWR_GET_FLAG(PWR_FLAG_VOSRDY)) {
    }

    /* Enable HSE Oscillator and activate PLL with HSE as source */
    RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE | RCC_OSCILLATORTYPE_HSI48;
    RCC_OscInitStruct.HSEState       = RCC_HSE_ON;
    RCC_OscInitStruct.HSIState       = RCC_HSI_OFF;
    RCC_OscInitStruct.CSIState       = RCC_CSI_OFF;
    RCC_OscInitStruct.HSI48State     = RCC_HSI48_ON;
    RCC_OscInitStruct.PLL.PLLState   = RCC_PLL_ON;
    RCC_OscInitStruct.PLL.PLLSource  = RCC_PLLSOURCE_HSE;

    RCC_OscInitStruct.PLL.PLLM = 1;
    RCC_OscInitStruct.PLL.PLLN = 120;
    RCC_OscInitStruct.PLL.PLLP = 2;
#ifdef SCREEN_MODE_COLOR
    RCC_OscInitStruct.PLL.PLLQ = 8;
#else
    RCC_OscInitStruct.PLL.PLLQ = 120;
#endif
    RCC_OscInitStruct.PLL.PLLR     = 2;
    RCC_OscInitStruct.PLL.PLLFRACN = 0;

    RCC_OscInitStruct.PLL.PLLVCOSEL = RCC_PLL1VCOWIDE;
    RCC_OscInitStruct.PLL.PLLRGE    = RCC_PLL1VCIRANGE_1;
    rc                              = HAL_RCC_OscConfig(&RCC_OscInitStruct);
    if (rc != HAL_OK) {
        while (1) {
            ;
        }
    }

    PeriphClkInitStruct.PeriphClockSelection      = RCC_PERIPHCLK_RTC | RCC_PERIPHCLK_USART2 | RCC_PERIPHCLK_RNG;
    PeriphClkInitStruct.PLL2.PLL2M                = 1;
    PeriphClkInitStruct.PLL2.PLL2N                = 18;
    PeriphClkInitStruct.PLL2.PLL2P                = 1;
    PeriphClkInitStruct.PLL2.PLL2Q                = 2;
    PeriphClkInitStruct.PLL2.PLL2R                = 2;
    PeriphClkInitStruct.PLL2.PLL2RGE              = RCC_PLL2VCIRANGE_3;
    PeriphClkInitStruct.PLL2.PLL2VCOSEL           = RCC_PLL2VCOMEDIUM;
    PeriphClkInitStruct.PLL2.PLL2FRACN            = 6144;
    PeriphClkInitStruct.Usart234578ClockSelection = RCC_USART234578CLKSOURCE_D2PCLK1;
    PeriphClkInitStruct.RngClockSelection         = RCC_RNGCLKSOURCE_HSI48;
    PeriphClkInitStruct.RTCClockSelection         = RCC_RTCCLKSOURCE_LSI;
    rc                                            = HAL_RCCEx_PeriphCLKConfig(&PeriphClkInitStruct);
    if (rc != HAL_OK) {
        while (1) {
            ;
        }
    }

    RCC_ClkInitStruct.ClockType      = (RCC_CLOCKTYPE_SYSCLK | RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_D1PCLK1 |
                                   RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2 | RCC_CLOCKTYPE_D3PCLK1);
    RCC_ClkInitStruct.SYSCLKSource   = RCC_SYSCLKSOURCE_PLLCLK;
    RCC_ClkInitStruct.SYSCLKDivider  = RCC_SYSCLK_DIV1;
    RCC_ClkInitStruct.AHBCLKDivider  = RCC_HCLK_DIV2;
    RCC_ClkInitStruct.APB3CLKDivider = RCC_APB3_DIV2;
    RCC_ClkInitStruct.APB1CLKDivider = RCC_APB1_DIV2;
    RCC_ClkInitStruct.APB2CLKDivider = RCC_APB2_DIV2;
    RCC_ClkInitStruct.APB4CLKDivider = RCC_APB4_DIV2;
    rc                               = HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_4);
    if (rc != HAL_OK) {
        while (1) {
            ;
        }
    }

    __HAL_RCC_CSI_ENABLE();
    __HAL_RCC_SYSCFG_CLK_ENABLE();
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();
    __HAL_RCC_GPIOD_CLK_ENABLE();
    __HAL_RCC_GPIOE_CLK_ENABLE();
    __HAL_RCC_D2SRAM1_CLK_ENABLE();
    __HAL_RCC_D2SRAM2_CLK_ENABLE();
    __HAL_RCC_D2SRAM3_CLK_ENABLE();
}

// Recover from ECC errors during firmware updates
void HardFault_Handler(void) {
    uint32_t cfsr = SCB->CFSR;

    if (cfsr & 0x8000) {
        uint32_t faultaddr       = (uint32_t)SCB->BFAR;
        uint32_t fw_sector_start = FW_START;
        uint32_t fw_sector_end   = FW_END;

        if ((faultaddr >= fw_sector_start) && (faultaddr < fw_sector_end)) {
            uint32_t faultsector = faultaddr & 0xFFF0000;

            flash_unlock();
            flash_sector_erase(faultsector);
            flash_lock();

            /* Reset the board */
            passport_reset();
        }
    }

    while (1)
        ;
}

static void MPU_Config(void) {
    MPU_Region_InitTypeDef MPU_InitStruct;

    /* Disable MPU */
    HAL_MPU_Disable();

    /* Configure AXI SRAM region as non-executable */
    memset(&MPU_InitStruct, 0, sizeof(MPU_InitStruct));
    MPU_InitStruct.Enable           = MPU_REGION_ENABLE;
    MPU_InitStruct.BaseAddress      = 0x24000000;
    MPU_InitStruct.Size             = MPU_REGION_SIZE_512KB;
    MPU_InitStruct.AccessPermission = MPU_REGION_FULL_ACCESS;
    MPU_InitStruct.IsBufferable     = MPU_ACCESS_NOT_BUFFERABLE;
    MPU_InitStruct.IsCacheable      = MPU_ACCESS_CACHEABLE;
    MPU_InitStruct.IsShareable      = MPU_ACCESS_SHAREABLE;
    MPU_InitStruct.Number           = MPU_REGION_NUMBER0;
    MPU_InitStruct.TypeExtField     = MPU_TEX_LEVEL0;
    MPU_InitStruct.SubRegionDisable = 0x00;
    MPU_InitStruct.DisableExec      = MPU_INSTRUCTION_ACCESS_DISABLE;
    HAL_MPU_ConfigRegion(&MPU_InitStruct);

    /* Configure SRAM1 region as non-executable */
    memset(&MPU_InitStruct, 0, sizeof(MPU_InitStruct));
    MPU_InitStruct.Enable           = MPU_REGION_ENABLE;
    MPU_InitStruct.BaseAddress      = 0x30000000;
    MPU_InitStruct.Size             = MPU_REGION_SIZE_128KB;
    MPU_InitStruct.AccessPermission = MPU_REGION_FULL_ACCESS;
    MPU_InitStruct.IsBufferable     = MPU_ACCESS_NOT_BUFFERABLE;
    MPU_InitStruct.IsCacheable      = MPU_ACCESS_CACHEABLE;
    MPU_InitStruct.IsShareable      = MPU_ACCESS_SHAREABLE;
    MPU_InitStruct.Number           = MPU_REGION_NUMBER1;
    MPU_InitStruct.TypeExtField     = MPU_TEX_LEVEL0;
    MPU_InitStruct.SubRegionDisable = 0x00;
    MPU_InitStruct.DisableExec      = MPU_INSTRUCTION_ACCESS_DISABLE;
    HAL_MPU_ConfigRegion(&MPU_InitStruct);

    /* Configure SRAM2 region as non-executable */
    memset(&MPU_InitStruct, 0, sizeof(MPU_InitStruct));
    MPU_InitStruct.Enable           = MPU_REGION_ENABLE;
    MPU_InitStruct.BaseAddress      = 0x30020000;
    MPU_InitStruct.Size             = MPU_REGION_SIZE_128KB;
    MPU_InitStruct.AccessPermission = MPU_REGION_FULL_ACCESS;
    MPU_InitStruct.IsBufferable     = MPU_ACCESS_NOT_BUFFERABLE;
    MPU_InitStruct.IsCacheable      = MPU_ACCESS_CACHEABLE;
    MPU_InitStruct.IsShareable      = MPU_ACCESS_SHAREABLE;
    MPU_InitStruct.Number           = MPU_REGION_NUMBER2;
    MPU_InitStruct.TypeExtField     = MPU_TEX_LEVEL0;
    MPU_InitStruct.SubRegionDisable = 0x00;
    MPU_InitStruct.DisableExec      = MPU_INSTRUCTION_ACCESS_DISABLE;
    HAL_MPU_ConfigRegion(&MPU_InitStruct);

    /* Configure SRAM3 region as non-executable */
    memset(&MPU_InitStruct, 0, sizeof(MPU_InitStruct));
    MPU_InitStruct.Enable           = MPU_REGION_ENABLE;
    MPU_InitStruct.BaseAddress      = 0x30040000;
    MPU_InitStruct.Size             = MPU_REGION_SIZE_32KB;
    MPU_InitStruct.AccessPermission = MPU_REGION_FULL_ACCESS;
    MPU_InitStruct.IsBufferable     = MPU_ACCESS_NOT_BUFFERABLE;
    MPU_InitStruct.IsCacheable      = MPU_ACCESS_CACHEABLE;
    MPU_InitStruct.IsShareable      = MPU_ACCESS_SHAREABLE;
    MPU_InitStruct.Number           = MPU_REGION_NUMBER3;
    MPU_InitStruct.TypeExtField     = MPU_TEX_LEVEL0;
    MPU_InitStruct.SubRegionDisable = 0x00;
    MPU_InitStruct.DisableExec      = MPU_INSTRUCTION_ACCESS_DISABLE;
    HAL_MPU_ConfigRegion(&MPU_InitStruct);

    /* Configure SRAM4 region as non-executable */
    memset(&MPU_InitStruct, 0, sizeof(MPU_InitStruct));
    MPU_InitStruct.Enable           = MPU_REGION_ENABLE;
    MPU_InitStruct.BaseAddress      = 0x38000000;
    MPU_InitStruct.Size             = MPU_REGION_SIZE_64KB;
    MPU_InitStruct.AccessPermission = MPU_REGION_FULL_ACCESS;
    MPU_InitStruct.IsBufferable     = MPU_ACCESS_NOT_BUFFERABLE;
    MPU_InitStruct.IsCacheable      = MPU_ACCESS_CACHEABLE;
    MPU_InitStruct.IsShareable      = MPU_ACCESS_SHAREABLE;
    MPU_InitStruct.Number           = MPU_REGION_NUMBER4;
    MPU_InitStruct.TypeExtField     = MPU_TEX_LEVEL0;
    MPU_InitStruct.SubRegionDisable = 0x00;
    MPU_InitStruct.DisableExec      = MPU_INSTRUCTION_ACCESS_DISABLE;
    HAL_MPU_ConfigRegion(&MPU_InitStruct);

    /* Configure ITCM region as non-executable */
    memset(&MPU_InitStruct, 0, sizeof(MPU_InitStruct));
    MPU_InitStruct.Enable           = MPU_REGION_ENABLE;
    MPU_InitStruct.BaseAddress      = 0x00000000;
    MPU_InitStruct.Size             = MPU_REGION_SIZE_64KB;
    MPU_InitStruct.AccessPermission = MPU_REGION_FULL_ACCESS;
    MPU_InitStruct.IsBufferable     = MPU_ACCESS_NOT_BUFFERABLE;
    MPU_InitStruct.IsCacheable      = MPU_ACCESS_CACHEABLE;
    MPU_InitStruct.IsShareable      = MPU_ACCESS_SHAREABLE;
    MPU_InitStruct.Number           = MPU_REGION_NUMBER5;
    MPU_InitStruct.TypeExtField     = MPU_TEX_LEVEL0;
    MPU_InitStruct.SubRegionDisable = 0x00;
    MPU_InitStruct.DisableExec      = MPU_INSTRUCTION_ACCESS_DISABLE;
    HAL_MPU_ConfigRegion(&MPU_InitStruct);

    /* Configure DTCM region as non-executable */
    memset(&MPU_InitStruct, 0, sizeof(MPU_InitStruct));
    MPU_InitStruct.Enable           = MPU_REGION_ENABLE;
    MPU_InitStruct.BaseAddress      = 0x20000000;
    MPU_InitStruct.Size             = MPU_REGION_SIZE_128KB;
    MPU_InitStruct.AccessPermission = MPU_REGION_FULL_ACCESS;
    MPU_InitStruct.IsBufferable     = MPU_ACCESS_NOT_BUFFERABLE;
    MPU_InitStruct.IsCacheable      = MPU_ACCESS_CACHEABLE;
    MPU_InitStruct.IsShareable      = MPU_ACCESS_SHAREABLE;
    MPU_InitStruct.Number           = MPU_REGION_NUMBER5;
    MPU_InitStruct.TypeExtField     = MPU_TEX_LEVEL0;
    MPU_InitStruct.SubRegionDisable = 0x00;
    MPU_InitStruct.DisableExec      = MPU_INSTRUCTION_ACCESS_DISABLE;
    HAL_MPU_ConfigRegion(&MPU_InitStruct);

    /* Configure Backup region as non-executable */
    memset(&MPU_InitStruct, 0, sizeof(MPU_InitStruct));
    MPU_InitStruct.Enable           = MPU_REGION_ENABLE;
    MPU_InitStruct.BaseAddress      = 0x38800000;
    MPU_InitStruct.Size             = MPU_REGION_SIZE_4KB;
    MPU_InitStruct.AccessPermission = MPU_REGION_FULL_ACCESS;
    MPU_InitStruct.IsBufferable     = MPU_ACCESS_NOT_BUFFERABLE;
    MPU_InitStruct.IsCacheable      = MPU_ACCESS_CACHEABLE;
    MPU_InitStruct.IsShareable      = MPU_ACCESS_SHAREABLE;
    MPU_InitStruct.Number           = MPU_REGION_NUMBER5;
    MPU_InitStruct.TypeExtField     = MPU_TEX_LEVEL0;
    MPU_InitStruct.SubRegionDisable = 0x00;
    MPU_InitStruct.DisableExec      = MPU_INSTRUCTION_ACCESS_DISABLE;
    HAL_MPU_ConfigRegion(&MPU_InitStruct);

    /* Enable MPU */
    HAL_MPU_Enable(MPU_PRIVILEGED_DEFAULT);
}

static void version(void) {
    passport_firmware_header_t* fwhdr       = (passport_firmware_header_t*)FW_HDR;
    char                        version[22] = {0};

    strcpy(version, "Version ");
    strcat(version, (char*)fwhdr->info.fwversion);

    show_splash(version);
}

#ifndef FACTORY_TEST
uint8_t handle_page_key(KEY_ID key, uint8_t curr_page, uint8_t num_pages) {
    if (key == KEY_LEFT_SELECT) {
        ui_ask_shutdown();
        return curr_page;
    } else if (key == KEY_RIGHT) {
        if (curr_page < num_pages - 1) {
            return curr_page + 1;
        }

    } else if (key == KEY_LEFT) {
        if (curr_page > 0) {
            return curr_page - 1;
        }
    }
    return curr_page;
}

bool ask_to_start() {
    return ui_show_question("SYSTEM INFO", "Start Passport?", "Exit System Info and start Passport now?", true) ==
           KEY_RIGHT_SELECT;
}

#define NUM_INFO_PAGES 4
static void show_more_info(void) {
    char message[80];

    // For the firmware header and hash
    uint8_t                     fw_hash[HASH_LEN];
    passport_firmware_header_t* fwhdr = (passport_firmware_header_t*)FW_HDR;

    uint8_t page    = 0;
    char*   heading = "SYSTEM INFO";

    while (true) {
        KEY_ID key;
        switch (page) {
            case 0:
                strcpy(message, "Version ");
                strcat(message, build_version);
                strcat(message, "\n\nBuilt on ");
                strcat(message, build_date);

                key = ui_show_page(heading, "Bootloader Info", message, &LARGE_ICON_INFO, &ICON_SHUTDOWN, &ICON_EXIT,
                                   true, page, NUM_INFO_PAGES);
                if (key == KEY_RIGHT_SELECT) {
                    if (ask_to_start()) {
                        return;
                    }
                }
                page = handle_page_key(key, page, NUM_INFO_PAGES);
                break;

            case 1:
                strcpy(message, "Version ");
                strcat(message, (char*)fwhdr->info.fwversion);
                strcat(message, "\n\nBuilt on ");
                strcat(message, (char*)fwhdr->info.fwdate);
                key = ui_show_page(heading, "Firmware Info", message, &LARGE_ICON_INFO, &ICON_SHUTDOWN, &ICON_EXIT,
                                   true, page, NUM_INFO_PAGES);
                if (key == KEY_RIGHT_SELECT) {
                    if (ask_to_start()) {
                        return;
                    }
                }
                page = handle_page_key(key, page, NUM_INFO_PAGES);
                break;

            case 2: {
                strcpy(message, "");
                hash_fw_user((uint8_t*)fwhdr, FW_HEADER_SIZE + fwhdr->info.fwlength, fw_hash, sizeof(fw_hash), false);

                bytes_to_hex_str(fw_hash, 32, &message[strlen(message)], 8, "\n");

                key = ui_show_page(heading, "Firmware Hash", message, &LARGE_ICON_INFO, &ICON_SHUTDOWN, &ICON_EXIT,
                                   true, page, NUM_INFO_PAGES);
                if (key == KEY_RIGHT_SELECT) {
                    if (ask_to_start()) {
                        return;
                    }
                }
                page = handle_page_key(key, page, NUM_INFO_PAGES);
                break;
            }

            case 3: {
                strcpy(message, "");
                hash_fw_user((uint8_t*)fwhdr, FW_HEADER_SIZE + fwhdr->info.fwlength, fw_hash, sizeof(fw_hash), true);

                bytes_to_hex_str(fw_hash, 32, &message[strlen(message)], 8, "\n");

                key = ui_show_page(heading, "Build Hash", message, &LARGE_ICON_INFO, &ICON_SHUTDOWN, &ICON_EXIT, true,
                                   page, NUM_INFO_PAGES);
                if (key == KEY_RIGHT_SELECT) {
                    if (ask_to_start()) {
                        return;
                    }
                }
                page = handle_page_key(key, page, NUM_INFO_PAGES);
                break;
            }
        }
    }
}

#ifdef DEBUG_DUMP
void dump_spi_flash() {
    uint8_t                    data[256]     = {0};
    char                       str_buf[1024] = {0};
    passport_firmware_header_t sd_card_hdr   = {0};
    if (spi_read(256, sizeof(passport_firmware_header_t), (uint8_t*)&sd_card_hdr) != HAL_OK) {
        printf("ERROR: Unable to read SPI header for dump\r\n");
        return;
    }
    uint32_t fwlength = sd_card_hdr.info.fwlength;
    printf("fwlength=%lu\r\n", fwlength);
    if (fwlength < 1570000) {
        printf("ERROR: fwlength is too small...doesn't look like firmware is in SPI flash\r\n");
        return;
    }
    if (fwlength > 1700000) {
        printf("ERROR: fwlength is too big...doesn't look like firmware is in SPI flash\r\n");
        return;
    }
    uint32_t total_length = FW_HEADER_SIZE + fwlength;
    printf("total_length=%lu\r\n", total_length);

    printf("======================================== SPI Flash Contents ========================================\r\n");
    for (uint32_t addr = 256; addr < total_length + 256; addr += SPI_FLASH_PAGE_SIZE) {
        uint32_t          len_to_read = MIN(SPI_FLASH_PAGE_SIZE, (total_length + 256) - addr);
        HAL_StatusTypeDef status      = spi_read(addr, len_to_read, data);
        if (status != HAL_OK) {
            printf("ERROR: spi_read() failed: addr=0x%08lx\r\n", addr);
        }

        bytes_to_hex_str(data, len_to_read, str_buf, 64, "\r\n");
        printf("%s\r\n", str_buf);
    }
    printf(
        "======================================== SPI Flash Contents ========================================\r\n\r\n");
}

void dump_internal_flash() {
    char                        str_buf[256] = {0};
    passport_firmware_header_t* sd_card_hdr  = (passport_firmware_header_t*)FW_START;

    uint32_t fwlength = sd_card_hdr->info.fwlength;
    printf("fwlength=%lu\r\n", fwlength);
    uint32_t total_length = FW_HEADER_SIZE + fwlength;
    printf("total_length=%lu\r\n", total_length);

    printf("====================================== Internal Flash Contents =====================================\r\n");
    for (uint32_t addr = 0; addr < total_length; addr += SPI_FLASH_PAGE_SIZE) {
        uint32_t len_to_dump = MIN(SPI_FLASH_PAGE_SIZE, total_length - addr);

        bytes_to_hex_str((uint8_t*)(FW_START + addr), len_to_dump, str_buf, 64, "\r\n");
        printf("%s\r\n", str_buf);
    }
    printf(
        "====================================== Internal Flash Contents =====================================\r\n\r\n");
}
#endif

static void microsd_firmware_recovery(void) {
    HAL_StatusTypeDef          res;
    passport_firmware_header_t sd_card_hdr = {0};
    char                       message[120];

retry:
    // Ask to insert SD card if it's not present yet.
    while (true) {
        sd_init();

        if (is_sd_card_present()) {
            break;
        }
        if (ui_show_missing_microsd("FIRMWARE RECOVERY", "No microSD",
                                    "Please insert a microSD card with an official Passport firmware image and retry.",
                                    &ICON_SHUTDOWN, &ICON_RETRY, true) != KEY_RIGHT_SELECT) {
            ui_ask_shutdown();
        }
    }

    if ((res = sd_card_init()) != HAL_OK) {
        strcpy(message, "Unable to read from microSD.");
        goto fail;
    }

    if (sd_read_block(0, sizeof(passport_firmware_header_t), (uint8_t*)&sd_card_hdr) != HAL_OK) {
        strcpy(message, "Unable to read from microSD.");
        goto fail;
    }

    if (!verify_header(&sd_card_hdr)) {
        if (ui_show_error("FIRMWARE RECOVERY", "Recovery Error",
                          "This microSD card does not contain a valid Passport firmware image.", &ICON_SHUTDOWN,
                          &ICON_RETRY, true) == KEY_RIGHT_SELECT) {
            goto retry;
        } else {
            ui_ask_shutdown();
            goto retry;
        }
    }

    // User signed firmware cannot be used as a factory reset firmware.
    if (sd_card_hdr.signature.pubkey1 == FW_USER_KEY && sd_card_hdr.signature.pubkey2 == 0) {
        strcpy(message, "Firmware signed by a Developer PubKey cannot be used for recovery.");
        goto fail;
    }

#ifdef PRODUCTION_BUILD
    uint8_t current_board_hash[HASH_LEN] = {0};
    get_current_board_hash(current_board_hash);

    // Version downgrade check
    uint32_t current_firmware_timestamp = se_get_firmware_timestamp(current_board_hash);

    if (sd_card_hdr.info.timestamp < current_firmware_timestamp) {
    downgrade_error:
        if (ui_show_error("PASSPORT", "Recovery Error",
                          "This firmware is older than the last installed official firmware and will not be installed.",
                          &ICON_SHUTDOWN, &ICON_CHECKMARK, true) == KEY_RIGHT_SELECT) {
            clear_update_from_spi_flash(FW_HEADER_SIZE + sd_card_hdr.info.fwlength);
            return;
        } else {
            ui_ask_shutdown();
            goto downgrade_error;
        }
    }
#endif  // PRODUCTION_BUILD

    strcpy(message, "Install this firmware?\n\n");
    strcat(message, "Version ");
    strcat(message, (char*)sd_card_hdr.info.fwversion);
    strcat(message, "\nBuilt on ");
    strcat(message, (char*)sd_card_hdr.info.fwdate);

ask_to_recover:
    if (ui_show_question("FIRMWARE RECOVERY", "Recover Passport", message, true) == KEY_RIGHT_SELECT) {
        // Copy firmware blocks to the SPI flash memory
        copy_firmware_from_sd_to_spi(&sd_card_hdr);
        update_firmware();
    } else {
        ui_ask_shutdown();
        goto ask_to_recover;
    }
    return;

fail:

    if (ui_show_error("FIRMWARE RECOVERY", "Recovery Error", message, &ICON_SHUTDOWN, &ICON_CHECKMARK, true) ==
        KEY_LEFT_SELECT) {
        ui_ask_shutdown();
    }
}
#endif /* FACTORY_TEST */

void random_boot_delay() {
    // Random delay to make cold-boot stepping attacks harder: 0 - 50ms
    uint32_t ms_to_delay = rng_sample() % 50;
    delay_ms(ms_to_delay);
}

void do_verify_current_firmware() {
    // Validate the internal firmware
    secresult result = verify_current_firmware(true);
    switch (result) {
        case SEC_TRUE:
            // All good!
            break;

        case ERR_INVALID_FIRMWARE_HEADER:
            ui_show_fatal_error("Invalid firmware header.\n\nThis Passport is now permanently disabled.");
            break;

        case ERR_INVALID_FIRMWARE_SIGNATURE:
            ui_show_fatal_error("Unsigned firmware installed.\n\nThis Passport is now permanently disabled.");
            break;

        case ERR_FIRMWARE_HASH_DOES_NOT_MATCH_SE:
            ui_show_fatal_error("Incorrect firmware hash.\n\nThis Passport is now permanently disabled.");
            break;

        default:
            ui_show_fatal_error("Unexpected error when verifying current firmware.");
            break;
    }
}

#ifdef SE_FIRMWARE_HASH_TEST
// Repeatedly set the firmware hash to see if the SE ever fails
void test_se_firmware_hash() {
    uint8_t  hash0[HASH_LEN] = {0x7E, 0x45, 0x1E, 0xBD, 0xD0, 0x4A, 0x37, 0xE5, 0x9F, 0xF1, 0x1E,
                                0xD5, 0xE3, 0x02, 0xCD, 0xB6, 0x5A, 0x89, 0x15, 0xD7, 0x42, 0x56,
                                0xE5, 0xC2, 0xB3, 0x0C, 0xFD, 0x7C, 0x79, 0x28, 0x5A, 0x4E};
    uint8_t  hash1[HASH_LEN] = {0xF9, 0x38, 0x67, 0xF2, 0x41, 0xDF, 0x37, 0x81, 0x5C, 0xBD, 0x52,
                                0x72, 0xBF, 0xE5, 0x40, 0xFF, 0xEF, 0xB7, 0x91, 0x74, 0xC5, 0x98,
                                0xDA, 0x80, 0x3C, 0xFA, 0xF5, 0x2E, 0x66, 0x3C, 0x9B, 0xBC};
    uint32_t errors          = 0;
    for (uint32_t i = 0; i < 2; i++) {
        printf("Iteration:%lu\r\n", i);
        int rc;
        if (i % 2 == 0) {
            rc = se_program_board_hash(hash0, hash1);

        } else {
            rc = se_program_board_hash(hash1, hash0);
        }
        if (rc != 0) {
            errors++;
            printf("ERROR: Failed to set board hash with i=%lu rc=%d\r\n", i, rc);
        }
    }
    printf("========================\r\n");
    printf("Errors: %lu\r\n", errors);
    printf("========================\r\n");
}
#endif

int main(void) {
    HAL_StatusTypeDef rc;
#ifndef FACTORY_TEST
    uint8_t key;
#endif /* FACTORY_TEST */
    SystemInit();

    rc = HAL_Init();
    if (rc != HAL_OK) LOCKUP_FOREVER();

#if 0 /* This is interfering with firmware boot after an update. It
       * appears that the data cache is getting in the way of the
       * reset handler properly copying over the data section into SRAM.
       */
    SCB_EnableICache();
    SCB_EnableDCache();
#endif
    SystemClock_Config();

    // Set Brown-out level early on to reset on glitch attempts
    MODIFY_REG(FLASH->OPTSR_PRG, FLASH_OPTSR_BOR_LEV, (uint32_t)OB_BOR_LEVEL2);

    // Enable printfs to UART console
    init_console_uart();

#ifdef FACTORY_TEST
    // Initialize the LCD driver and clear the display
    display_init(true);
    backlight_init();
    backlight_intensity(100);

    keypad_init();
    gpio_init();

    show_splash("");

    factory_test_loop();
#endif

#ifdef LOCKED
    if (flash_is_programmed() == SEC_TRUE) {
        // Ensure RDP level 2 on every boot in case of shenanigans
        if (!flash_is_security_level2()) {
            flash_lockdown_hard();
        }
    }
#endif /* LOCKED */

    rng_setup();

    random_boot_delay();

    se_setup();

    // Force LED to red every time we restart for consistency
    se_set_gpio(0);

    // Show a banner
    printf("================================================================================\r\n\r\n");
    printf("  ######      #       ######    ######   ######     #####    ######   ########\r\n");
    printf("  ##   ##    ###     ##        ##        ##   ##   ##   ##   ##   ##     ##\r\n");
    printf("  #######   ## ##     #####     #####    #######   ##   ##   #######     ##\r\n");
    printf("  ##       ##   ##        ##        ##   ##        ##   ##   ##  ##      ##\r\n");
    printf("  ##      ##     ##  ######    ######    ##         #####    ##   ##     ##\r\n\r\n");

    printf("                            Bootloader Version %s\r\n", build_version);
    printf("================================================================================\r\n\r\n");

    // Initialize the LCD driver and clear the display
    display_init(true);

    gpio_init();
    keypad_init();

    eeprom_init(&g_hi2c2);

    // In case brightness ever gets out of range, fix it. Value of 5 is minimum you can still see.
    uint16_t brightness = eeprom_get_screen_brightness(100);
    if (brightness < 5 || brightness > 100) {
        brightness = 100;
        eeprom_set_screen_brightness(brightness);
    }
    // printf("EEPROM brightness=%u\r\n", brightness);

    backlight_init();
    backlight_intensity(brightness);

    show_splash("Validating Firmware...");

    random_boot_delay();

#ifndef FACTORY_TEST
    // Check for first-boot condition
    if (flash_is_programmed() == SEC_FALSE) {
        // Force screen brightness to 100% on first boot to initialize it
        eeprom_set_screen_brightness(100);

        secresult result = flash_first_boot();
        switch (result) {
            case SEC_TRUE:
                // All good!
                break;

            case ERR_ROM_SECRETS_TOO_BIG:
                ui_show_fatal_error("ROM Secrets area is larger than 2048 bytes.");
                break;

            case ERR_INVALID_FIRMWARE_HEADER:
                ui_show_fatal_error("Invalid firmware header found during first boot.");
                break;

            case ERR_INVALID_FIRMWARE_SIGNATURE:
                ui_show_fatal_error("Invalid firmware signature found during first boot.");
                break;

            case ERR_UNABLE_TO_CONFIGURE_SE:
                ui_show_fatal_error("Unable to configure the Secure Element during first boot.");
                break;

            case ERR_UNABLE_TO_WRITE_ROM_SECRETS:
                ui_show_fatal_error("Unable to flash ROM secrets to end of bootloader flash block during first boot.");
                break;

            case ERR_UNABLE_TO_PROGRAM_FIRMWARE_HASH_IN_SE:
                ui_show_fatal_error("Unable to program firmware hash into Secure Element during first boot.");
                break;

            case ERR_UNABLE_TO_SET_FIRMWARE_TIMESTAMP_IN_SE:
                ui_show_fatal_error("Unable to set firmware timestamp in Secure Element during first boot.");
                break;

            default:
                ui_show_fatal_error("Unexpected error on first boot.");
                break;
        }
#ifdef LOCKED
        // Ensure RDP level 2 on every boot in case of shenanigans
        if (!flash_is_security_level2()) {
            flash_lockdown_hard();
        }
#endif
    }

    // Increment the boot counter
    uint32_t counter_result;
    if (se_add_counter(&counter_result, 1, 1) != 0) {
        ui_show_fatal_error("Boot counter failure.\n\nThis Passport is now permanently disabled.");
    }

    // Validate our pairing secret
    if (!se_valid_secret(rom_secrets->pairing_secret)) {
        ui_show_fatal_error("Secure Element error.\n\nThis Passport is now permanently disabled.");
    }

    // Setup MPU
    MPU_Config();

    // Check for firmware update
    if (is_firmware_update_present() == SEC_TRUE) {
        update_firmware();
    }

    do_verify_current_firmware();

#endif /* ifndef FACTORY_TEST */

    random_boot_delay();

    version();

#ifndef FACTORY_TEST
    /*
     * Delay for 3 seconds to allow the user to press a key indicating that
     * they would like to see board info or show the self test (in Python),
     * or enter firmware recovery mode.
     */
    delay_ms(3000);

    // We use the first byte in sram4 to pass a parameter that we check for on the MicroPython side
    // to see if user wants to view the self-test.
    uint8_t* p_sram4 = (uint8_t*)0x38000000;
    *p_sram4         = 0;

    if (keypad_poll_key(&key)) {
        // The '1' key
        if ((key & 0x7f) == KEY_1) {
            show_more_info();
        }

        // The '7' key
        if ((key & 0x7f) == KEY_7) {
            // Setting this byte to 1 signals main.py to show the self-test
            *p_sram4 = 1;
        }

        // The '9' key
        if ((key & 0x7f) == KEY_9) {
            microsd_firmware_recovery();

            version();

            // Final verification after installing the new firmware
            do_verify_current_firmware();
        }
    }

    // Show a warning message if user-signed firmware (including Foundation Beta firmware) is loaded on the device
    if (is_user_signed_firmware_installed() == SEC_TRUE) {
        while (true) {
            if (ui_show_error("PASSPORT", "WARNING!", "Custom firmware is loaded on this Passport.\n\nOK to continue?",
                              &ICON_SHUTDOWN, &ICON_CHECKMARK, true) == KEY_RIGHT_SELECT) {
                // Continue booting
                version();
                break;
            } else {
                ui_ask_shutdown();
                // else loop around and show the warning again
            }
        }
    }

#endif /* FACTORY_TEST */
    // From here we'll boot to Micropython: see stm32_main() in /ports/stm32/main.c
}
