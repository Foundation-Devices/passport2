// SPDX-FileCopyrightText: 2022 Foundation Devices, Inc.
// <hello@foundationdevices.com> SPDX-License-Identifier: GPL-3.0-or-later
//
// SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
// SPDX-License-Identifier: GPL-3.0-only
//
/*
 * (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
 * and is covered by GPLv3 license found in COPYING.
 *
 * update.c -- firmware update processing
 *
 */

#include <stdlib.h>
#include <string.h>
#include <assert.h>

#include "display.h"
#include "fwheader.h"
#include "hash.h"
#include "se-config.h"
#include "se.h"
#include "sha256.h"
#include "spiflash.h"
#include "splash.h"
#include "utils.h"

#include "firmware-keys.h"
#include "flash.h"
#include "gpio.h"
#include "se-atecc608a.h"
#include "lvgl.h"
#include "images.h"
#include "ui.h"
#include "update.h"
#include "verify.h"
#include "sd.h"
#include "eeprom.h"
#include "delay.h"

// #define DEBUG_PRINT_CALC_HASH
// #define DEBUG_PRINT_UPDATE_HASH
// #define DEBUG_PRINT_TIMESTAMP
// #define DEBUG_PRINT_SPI_HASH
// #define DEBUG_PRINT_COPY
// #define DEBUG_PRINT_SD_READS
// #define DEBUG_PRINT_SPI_WRITES
// #define DEBUG_PRINT_SPI_VERIFY_READS
// #define DEBUG_PRINT_VERIFY_ERRORS

#ifndef FACTORY_TEST

#if defined(DEBUG_PRINT_UPDATE_HASH) || defined(DEBUG_PRINT_SPI_HASH) || defined(DEBUG_PRINT_COPY) ||            \
    defined(DEBUG_PRINT_SD_READS) || defined(DEBUG_PRINT_SPI_WRITES) || defined(DEBUG_PRINT_SPI_VERIFY_READS) || \
    defined(DEBUG_PRINT_VERIFY_ERRORS) || defined(DEBUG_PRINT_CALC_HASH)
static char str_buf[16384];
#endif

extern void dump_spi_flash();

// Global so we can compare with it later in do_update()
static uint8_t spi_hdr_hash[HASH_LEN] = {0};

void clear_update_from_spi_flash(uint32_t total_size) {
    uint8_t zeros[FW_HEADER_SIZE] = {0};

    // Don't need to erase the entire SPI Flash.
    //
    // Just blow out the beginning...
    spi_write(0, 256, zeros);
    spi_write(256, sizeof(zeros), zeros);

    // and the end, so the hash won't match, even if the first part of the file is
    // written again by a subsequent update attempt.
    spi_write(total_size - sizeof(zeros), sizeof(zeros), zeros);
}

static void calculate_spi_hash(passport_firmware_header_t* hdr, uint8_t* hash, uint8_t hashlen) {
    SHA256_CTX ctx;
    uint32_t   pos       = FW_HEADER_SIZE + 256;  // Skip over the update hash page
    uint32_t   remaining = hdr->info.fwlength;
#ifdef DEBUG_PRINT_CALC_HASH
    printf("calculate_spi_hash(): pos=%lu\r\n", pos);
    printf("calculate_spi_hash(): remaining=%lu\r\n", remaining);
#endif
    uint8_t spi_data_buf[1024];

    sha256_init(&ctx);

    sha256_update(&ctx, (uint8_t*)&hdr->info, sizeof(fw_info_t));

    while (remaining > 0) {
        size_t bufsize;

        if (remaining >= sizeof(spi_data_buf))
            bufsize = sizeof(spi_data_buf);
        else
            bufsize = remaining;

        if (spi_read(pos, bufsize, spi_data_buf) != HAL_OK) goto out;

        sha256_update(&ctx, spi_data_buf, bufsize);
        remaining -= bufsize;
        pos += bufsize;
    }

    sha256_final(&ctx, hash);

    /* double SHA256 */
    sha256_init(&ctx);
    sha256_update(&ctx, hash, hashlen);
    sha256_final(&ctx, hash);

out:
    return;
}

static void calculate_spi_hdr_hash(passport_firmware_header_t* hdr, uint8_t* hash, uint8_t hashlen) {
    SHA256_CTX ctx;

    sha256_init(&ctx);
    sha256_update(&ctx, (uint8_t*)hdr, sizeof(passport_firmware_header_t));
    sha256_final(&ctx, hash);

    /* double SHA256 */
    sha256_init(&ctx);
    sha256_update(&ctx, hash, hashlen);
    sha256_final(&ctx, hash);
}

// Hash the spi hash with the device hash value -- used to prevent external attacker from being able to insert a firmware
// update directly in external SPI flash. They won't be able to replicate this hash.
void calculate_update_hash(uint8_t* spi_hash, uint8_t spi_hashlen, uint8_t* update_hash, uint8_t update_hashlen) {
    SHA256_CTX ctx;

    uint8_t device_hash[HASH_LEN];
    get_device_hash(device_hash);

    sha256_init(&ctx);
    sha256_update(&ctx, (uint8_t*)spi_hash, spi_hashlen);
    sha256_update(&ctx, device_hash, sizeof(device_hash));
    sha256_final(&ctx, update_hash);
}

static int do_update(uint32_t size) {
    int rc = 0;

    flash_unlock();

restart_update:
    do {
        uint8_t    flash_word_len = sizeof(uint32_t) * FLASH_NB_32BITWORD_IN_FLASHWORD;
        uint32_t   pos;
        uint32_t   addr;
        uint32_t   data[FLASH_NB_32BITWORD_IN_FLASHWORD] __attribute__((aligned(8)));
        uint32_t   total                       = FW_END - FW_START;
        uint8_t    percent_done                = 0;
        uint8_t    last_percent_done           = 255;
        uint8_t    curr_spi_hdr_hash[HASH_LEN] = {0};
        uint32_t   remaining_bytes_to_hash     = sizeof(passport_firmware_header_t);
        secresult  not_checked                 = SEC_TRUE;
        SHA256_CTX ctx;

        sha256_init(&ctx);

        // Make sure header still fits in one page or this check will be more complex.
        if (sizeof(passport_firmware_header_t) > 256) {
            clear_update_from_spi_flash(size);
            ui_show_fatal_error("sizeof(passport_firmware_header_t) > 256");
        }

        for (pos = 0, addr = FW_START; pos < size; pos += flash_word_len, addr += flash_word_len) {
            // Clear data buffer to zero
            memset(data, 0, sizeof(data));

            // We read starting 256 bytes in as the first page holds the update request hash, and that does
            // not get written to internal flash.
            uint32_t len_to_read = MIN(size - pos, sizeof(data));
            if (spi_read(pos + 256, len_to_read, (uint8_t*)data) != HAL_OK) {
                rc = -1;
                break;
            }

            // TOCTOU check by hashing the header again and comparing to the hash we took earlier when we verified it.
            if (remaining_bytes_to_hash > 0) {
                // Calculate the running hash 32 bytes at a time until we reach sizeof(passport_firmware_header_t)
                size_t hash_size = MIN(remaining_bytes_to_hash, flash_word_len);
                sha256_update(&ctx, (uint8_t*)data, hash_size);
                remaining_bytes_to_hash -= hash_size;
            }

            if (not_checked == SEC_TRUE && remaining_bytes_to_hash == 0) {
                // Finalize the hash and check it
                sha256_final(&ctx, curr_spi_hdr_hash);

                /* double SHA256 */
                sha256_init(&ctx);
                sha256_update(&ctx, curr_spi_hdr_hash, HASH_LEN);
                sha256_final(&ctx, curr_spi_hdr_hash);

                // Compare the hashes
                if (memcmp(curr_spi_hdr_hash, spi_hdr_hash, HASH_LEN) != 0) {
                    // Either got a bad read from SPI flash, or someone's tampering with it, so try again
                    // from the beginning.
                    printf("TOCTOU hash check failed - restarting the update!\r\n");
                    goto restart_update;
                }
                not_checked = SEC_FALSE;
            }

            if (addr % FLASH_SECTOR_SIZE == 0) {
                rc = flash_sector_erase(addr);
                if (rc < 0) break;
            }

            rc = flash_burn(addr, (uint32_t)data);
            if (rc < 0) break;

            // Verify that the data was written correctly
            uint8_t* internal_addr = (uint8_t*)addr;
            uint8_t* spi_data      = (uint8_t*)data;

            for (uint32_t i = 0; i < 32; i++) {
                if (internal_addr[i] != spi_data[i]) {
                    printf(
                        "Verify error at pos=%lu, addr=0x%08lux, expected=0x%02x, actual=0x%02x - restarting the update!\r\n",
                        pos, addr, spi_data[i], internal_addr[i]);
                    goto restart_update;
                }
            }

            /* Update the progress bar only if the percentage changed */
            percent_done = (uint8_t)((float)pos / (float)total * 100.0f);
            if (percent_done != last_percent_done) {
                display_progress_bar(PROGRESS_BAR_MARGIN, PROGRESS_BAR_Y, SCREEN_WIDTH - (PROGRESS_BAR_MARGIN * 2), 0,
                                     percent_done, "Updating Firmware...");
                last_percent_done = percent_done;
            }
        }

        /* Clear the remainder of flash */
        memset(data, 0, sizeof(data));
        for (; addr < FW_END; pos += flash_word_len, addr += flash_word_len) {
            if (addr % FLASH_SECTOR_SIZE == 0) {
                rc = flash_sector_erase(addr);
                if (rc < 0) break;
            }

            rc = flash_burn(addr, (uint32_t)data);
            if (rc < 0) break;

            /* Update the progress bar only if the percentage changed */
            percent_done = (uint8_t)((float)pos / (float)total * 100.0f);

            if (percent_done != last_percent_done) {
                display_progress_bar(PROGRESS_BAR_MARGIN, PROGRESS_BAR_Y, SCREEN_WIDTH - (PROGRESS_BAR_MARGIN * 2), 0,
                                     percent_done, "Updating Firmware...");

                last_percent_done = percent_done;
            }
        }

        /* Make sure the progress bar goes to 100 */
        display_progress_bar(PROGRESS_BAR_MARGIN, PROGRESS_BAR_Y, SCREEN_WIDTH - (PROGRESS_BAR_MARGIN * 2), 0, 100,
                             "Update Complete");
    } while (0);

    flash_lock();
    return rc;
}

secresult is_firmware_update_present(void) {
    passport_firmware_header_t hdr = {};

    if (spi_setup() != HAL_OK) return SEC_FALSE;

    // Skip first page of flash
    if (spi_read(256, sizeof(hdr), (void*)&hdr) != HAL_OK) return SEC_FALSE;

    if (!verify_header(&hdr)) return SEC_FALSE;

    return SEC_TRUE;
}

void update_firmware(void) {
    int                        rc;
    passport_firmware_header_t spihdr                         = {0};
    uint8_t                    spi_fw_hash[HASH_LEN]          = {0};
    uint8_t                    current_board_hash[HASH_LEN]   = {0};
    uint8_t                    new_board_hash[HASH_LEN]       = {0};
    uint8_t                    actual_update_hash[HASH_LEN]   = {0};
    uint8_t                    expected_update_hash[HASH_LEN] = {0};

    /*
     * If we fail to either setup the SPI bus or read the SPI flash
     * then just return...something is wrong in hardware but maybe it's
     * temporary.
     */
    if (spi_setup() != HAL_OK) return;

    // If the update was requested by the user, then there will be a hash in the first 32 bytes that combines
    // the firmware hash with the device hash.
    if (spi_read(0, HASH_LEN, (void*)&actual_update_hash) != HAL_OK) return;

    // Start reading one page in as there is a 32-byte hash in the first page
    if (spi_read(256, sizeof(spihdr), (void*)&spihdr) != HAL_OK) return;

    calculate_spi_hdr_hash(&spihdr, spi_hdr_hash, HASH_LEN);

    calculate_update_hash(spi_hdr_hash, sizeof(spi_hdr_hash), expected_update_hash, sizeof(expected_update_hash));

#ifdef DEBUG_PRINT_UPDATE_HASH
    bytes_to_hex_str((void*)expected_update_hash, sizeof(expected_update_hash), str_buf, 64, "\r\n");
    printf("expected_update_hash=%s\r\n", str_buf);

    bytes_to_hex_str((void*)actual_update_hash, sizeof(actual_update_hash), str_buf, 64, "\r\n");
    printf("actual_update_hash=%s\r\n", str_buf);
#endif

    // Ensure that the hashes match!
    if (memcmp(expected_update_hash, actual_update_hash, sizeof(expected_update_hash)) != 0) {
        // This looks like an unrequested update (i.e., a possible attack)
        printf("Update Hash Mismatch -- Aborting Update!\r\n");
        goto out;
    }

    /* Verify firmware header in SPI flash and bail if it fails */
    if (!verify_header(&spihdr)) {
    error1:
        if (ui_show_error("PASSPORT", "Update Error",
                          "The firmware update has an invalid header and will not be installed.", &ICON_SHUTDOWN,
                          &ICON_CHECKMARK, true) == KEY_RIGHT_SELECT) {
            goto out;
        } else {
            ui_ask_shutdown();
            goto error1;
        }
    }

    // Handle the firmware hash update
    get_current_board_hash(current_board_hash);

    /*
     * If the current firmware verification passes then compare timestamps and don't allow an earlier
     * version. However, if the internal firmware header verification fails then proceed with the
     * update...maybe the previous update attempt failed because we lost power.
     *
     * We also allow going back and forth between user-signed firmware and Foundation-signed firmware,
     * but the restriction is that the Foundation-signed firmware can't be older than the timestamp
     * stored in EEPROM.  We don't update the EEPROM timestamp for user-signed builds.
     */
#ifdef DEBUG_PRINT_UPDATE_HASH
    printf("Verifying current firmware before update\r\n");
#endif
    if (verify_current_firmware(true) == SEC_TRUE) {
#ifdef DEBUG_PRINT_UPDATE_HASH
        printf("  Current firmware is valid, so doing more checks.\r\n");
#endif

        bool is_spi_fw_user_signed = spihdr.signature.pubkey1 == FW_USER_KEY;

#ifdef PRODUCTION_BUILD
        uint32_t current_firmware_timestamp = se_get_firmware_timestamp(current_board_hash);
        if (current_firmware_timestamp == 0) {
        error2:
            if (ui_show_error("PASSPORT", "Update Error",
                              "Unable to read last firmware timestamp.\n\nFirmware will not be installed.",
                              &ICON_SHUTDOWN, &ICON_CHECKMARK, true) == KEY_RIGHT_SELECT)
                goto out;
            else {
                ui_ask_shutdown();
                goto error2;
            }
        }

#ifdef DEBUG_PRINT_TIMESTAMP
        printf("current_firmware_timestamp=%lu\r\n", current_firmware_timestamp);
        printf("spihdr.info.timestamp =%lu\r\n", spihdr.info.timestamp);
#endif

        if (!is_spi_fw_user_signed) {
            if (spihdr.info.timestamp < current_firmware_timestamp) {
            error3:
                if (ui_show_error("PASSPORT", "Update Error",
                                  "This firmware is older than the current firmware and will not be installed.",
                                  &ICON_SHUTDOWN, &ICON_CHECKMARK, true) == KEY_RIGHT_SELECT)
                    goto out;
                else {
                    ui_ask_shutdown();
                    goto error3;
                }
            }
        }
#endif

        calculate_spi_hash(&spihdr, spi_fw_hash, sizeof(spi_fw_hash));
#ifdef DEBUG_PRINT_UPDATE_HASH
        printf(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>\r\n");
        bytes_to_hex_str((void*)&spihdr, sizeof(spihdr), str_buf, 64, "\r\n");
        printf("spihdr\r\n%s\r\n", str_buf);
        bytes_to_hex_str((void*)spi_fw_hash, sizeof(spi_fw_hash), str_buf, 64, "\r\n");
        printf("spi_fw_hash\r\n%s\r\n", str_buf);
        printf(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>\r\n");
#endif
        // Verify the signature and bail if it fails
        if (verify_signature(&spihdr, spi_fw_hash, sizeof(spi_fw_hash)) == SEC_FALSE) {
        error4:
            if (ui_show_error("PASSPORT", "Update Error",
                              "The firmware update is not properly signed and will not be installed.", &ICON_SHUTDOWN,
                              &ICON_CHECKMARK, true) == KEY_RIGHT_SELECT) {
                goto out;
            } else {
                ui_ask_shutdown();
                goto error4;
            }
        }

        /*
         * Calculate a new board hash based on the SPI firmware and then
         * reprogram the board hash in the SE. If the update fails it
         * will be retried until it succeeds or the board is declared dead.
         */
        hash_board(spi_fw_hash, sizeof(spi_fw_hash), new_board_hash, sizeof(new_board_hash));

        rc = se_program_board_hash(current_board_hash, new_board_hash);
        if (rc < 0) {
        error5:
            if (ui_show_message(
                    "PASSPORT", "Update Error",
                    "Unable to update the firmware hash in the Secure Element. Update will continue, but may not be successful.",
                    &ICON_SHUTDOWN, &ICON_CHECKMARK, true) == KEY_RIGHT_SELECT) {
                // Nothing to do
            } else {
                ui_ask_shutdown();
                goto error5;
            }
        }

        // Update the firmware timestamp, but only if it's an official Foundation release.
        // NOTE: We need to use the new board hash here as we've just updated the SE with it,
        //       so the new one is required in order to write the timestamp.
        if (!is_spi_fw_user_signed) {
            rc = se_set_firmware_timestamp(new_board_hash, spihdr.info.timestamp);
            if (rc < 0) {
            error6:
                if (ui_show_error(
                        "PASSPORT", "Update Error",
                        "Unable to update the firmware timestamp. Update will continue, but may not be successful.",
                        &ICON_SHUTDOWN, &ICON_CHECKMARK, true) == KEY_RIGHT_SELECT) {
                    // Nothing to do
                } else {
                    ui_ask_shutdown();
                    goto error6;
                }
            }
        }
    }
#ifdef DEBUG_PRINT_UPDATE_HASH
    else {
        printf("  Current firmware is INVALID - fall through to try the update.\r\n");
    }
#endif

    rc = do_update(FW_HEADER_SIZE + spihdr.info.fwlength);
    if (rc < 0) {
    error7:
        if (ui_show_error("PASSPORT", "Update Error", "\nFailed to install the firmware update.", &ICON_SHUTDOWN,
                          &ICON_FORWARD, true) == KEY_RIGHT_SELECT)
            // TODO: Shoud we clear the update here or let it try again?
            passport_reset();
        else {
            // TODO: Should we have an option here to clear the SPI flash and restart (we could run a verify_current_firmware() first to make sure it's safe to boot there
            ui_ask_shutdown();
            goto error7;
        }
    }

out:
    clear_update_from_spi_flash(FW_HEADER_SIZE + spihdr.info.fwlength);
}

secresult is_user_signed_firmware_installed(void) {
    passport_firmware_header_t* hdr = FW_HDR;
    return (hdr->signature.pubkey1 == FW_USER_KEY && hdr->signature.pubkey2 == 0) ? SEC_TRUE : SEC_FALSE;
}

// Definitions for the code below
// ------------------------------
// page = smallest unit of flash (256 bytes)
// sector = 8 pages of flash (4K bytes)
// block = smallest unit of SD reading (512 bytes)
// chunk = a set of SD blocks (4K bytes)

#define SPI_PAGES_PER_SD_BLOCK (SD_BLOCK_SIZE_BYTES / SPI_FLASH_PAGE_SIZE)  // 2
#define SD_BLOCKS_PER_CHUNK 8
#define SD_CHUNK_SIZE (SD_BLOCK_SIZE_BYTES * SD_BLOCKS_PER_CHUNK)     // 4096
#define SPI_PAGES_PER_SD_CHUNK (SD_CHUNK_SIZE / SPI_FLASH_PAGE_SIZE)  // 8
#define MAX_SPI_PAGES_PER_SD_READ (SPI_PAGES_PER_SD_BLOCK * SD_BLOCKS_PER_READ)
#define SPI_SECTORS_PER_BLOCK (SD_BLOCKS_PER_READ / SPI_PAGES_PER_SD_BLOCK)

void copy_firmware_from_sd_to_spi(passport_firmware_header_t* hdr) {
    uint8_t update_hash[HASH_LEN]           = {0};
    uint8_t verify_buf[SPI_FLASH_PAGE_SIZE] = {0};

    assert(SPI_PAGES_PER_SD_BLOCK == 2);

    HAL_StatusTypeDef res;

    if (spi_setup() != HAL_OK) {
        return;
    }

    // Total size include the first page with the update hash
    uint32_t total_sd_data_len    = FW_HEADER_SIZE + hdr->info.fwlength;
    uint32_t total_spi_data_len   = SPI_FLASH_PAGE_SIZE + total_sd_data_len;
    uint32_t total_chunks         = (total_spi_data_len + SD_CHUNK_SIZE - 1) / SD_CHUNK_SIZE;
    uint8_t  chunk[SD_CHUNK_SIZE] = {0};

    uint32_t sd_bytes_remaining  = total_sd_data_len;
    uint32_t spi_bytes_remaining = total_spi_data_len;
    uint8_t  last_percent        = 0;

#ifdef DEBUG_PRINT_COPY
    printf("total_sd_data_len=%lu\r\n", total_sd_data_len);
    printf("total_spi_data_len=%lu\r\n", total_spi_data_len);
    printf("total_chunks=%lu\r\n", total_chunks);
    printf("sd_bytes_remaining=%lu\r\n", sd_bytes_remaining);
    printf("spi_bytes_remaining=%lu\r\n", spi_bytes_remaining);
#endif

    // NOTE: This code relies on sizeof chunk == sizeof sector to simplify it
    assert(SD_CHUNK_SIZE == SPI_FLASH_SECTOR_SIZE);

    // Show it once before we start copying
    display_progress_bar(PROGRESS_BAR_MARGIN, PROGRESS_BAR_Y, SCREEN_WIDTH - (PROGRESS_BAR_MARGIN * 2), 0, 0,
                         "Preparing Update...");

    // SPI chip needs 5ms after setup before it's ready to accept erase/write commands.
    delay_ms(6);

    // Iterate over all blocks
    uint32_t src_addr = 0;
    for (uint32_t sd_chunk_num = 0; sd_chunk_num < total_chunks; sd_chunk_num++) {
        // Special case for the first chunk
        if (sd_chunk_num == 0) {
#ifdef DEBUG_PRINT_COPY
            printf("sd_chunk_num=%lu (Special First Case)\r\n", sd_chunk_num);
#endif
            calculate_spi_hdr_hash(hdr, spi_hdr_hash, HASH_LEN);
            calculate_update_hash(spi_hdr_hash, sizeof(spi_hdr_hash), update_hash, sizeof(update_hash));

            // Clear the chunk to zeros and put the update_hash at the front
            memset(chunk, 0, SD_CHUNK_SIZE);
            memcpy(chunk, update_hash, sizeof(update_hash));

            // Even though the update hash is only 32 bytes, we skip the whole 256 byte page here.
            // Read an amount that is one page of bytes less.
            uint32_t sd_size_to_read = SD_CHUNK_SIZE - SPI_FLASH_PAGE_SIZE;
#ifdef DEBUG_PRINT_COPY
            printf("src_addr=%lu\r\n", src_addr);
            printf("sd_size_to_read=%lu\r\n", sd_size_to_read);
#endif
            if ((res = sd_read_block(src_addr, sd_size_to_read, chunk + SPI_FLASH_PAGE_SIZE)) != HAL_OK) {
                printf("sd_read_block(%d,) failed: %d\r\n", (unsigned int)src_addr, (unsigned int)res);
                return;
            }
#ifdef DEBUG_PRINT_SD_READS
            bytes_to_hex_str(chunk, SD_CHUNK_SIZE, str_buf, 64, "\r\n");
            printf("%s\r\n", str_buf);
#endif
            src_addr += sd_size_to_read;
            sd_bytes_remaining -= sd_size_to_read;
#ifdef DEBUG_PRINT_COPY
            printf("src_addr=%lu (Special First Case)\r\n", src_addr);
            printf("sd_bytes_remaining=%lu (Special First Case)\r\n", sd_bytes_remaining);
#endif
        } else {
#ifdef DEBUG_PRINT_COPY
            printf("sd_chunk_num=%lu (Normal Case)\r\n", sd_chunk_num);
#endif
            memset(chunk, 0, SD_CHUNK_SIZE);

            // Normal read
            uint32_t sd_size_to_read = MIN(sd_bytes_remaining, SD_CHUNK_SIZE);

#ifdef DEBUG_PRINT_COPY
            if (sd_size_to_read != SD_CHUNK_SIZE) {
                printf("sd_size_to_read=%lu (size of last Last fragment)\r\n", sd_chunk_num);
            }

            printf("src_addr=%lu (Normal Case)\r\n", src_addr);
            printf("sd_size_to_read=%lu (Normal Case)\r\n", sd_size_to_read);
#endif
            // Read the chunk (8 blocks, despite the function name)
            if ((res = sd_read_block(src_addr, sd_size_to_read, chunk)) != HAL_OK) {
#ifdef DEBUG_PRINT_COPY
                printf("sd_read_block(%d,) failed: %d\r\n", (unsigned int)src_addr, (unsigned int)res);
                bytes_to_hex_str(chunk, sd_size_to_read, str_buf, 64, "\r\n");
                printf("%s\r\n", str_buf);
#endif
                return;
            }
#ifdef DEBUG_PRINT_SD_READS
            bytes_to_hex_str(chunk, sd_size_to_read, str_buf, 64, "\r\n");
            printf("%s\r\n", str_buf);
#endif
            src_addr += sd_size_to_read;
            sd_bytes_remaining -= sd_size_to_read;
#ifdef DEBUG_PRINT_COPY
            printf("  AFTER CHUNK READ: src_addr=%lu (Normal Case)\r\n", src_addr);
            printf("  AFTER CHUNK READ: sd_bytes_remaining=%lu (Normal Case)\r\n", sd_bytes_remaining);
#endif
        }

        uint32_t dest_addr_base;
        uint32_t spi_bytes_remaining_at_start_of_chunk = spi_bytes_remaining;

    restart_chunk:
        // We have our block of data now, so erase the whole sector -- this adddress is the base for the
        // final dest_addr writes below.
        dest_addr_base = (sd_chunk_num * SD_CHUNK_SIZE);
        assert(dest_addr_base % SD_BLOCK_SIZE_BYTES == 0);
#ifdef DEBUG_PRINT_COPY
        printf("Erasing at dest_addr_base=0x%08lx\r\n", dest_addr_base);
#endif
        // #ifdef DEBUG_PRINT_VERIFY_ERRORS
        //         printf("Erasing at dest_addr_base=0x%08lx\r\n", dest_addr_base);
        // #endif

        if ((res = spi_sector_erase(dest_addr_base)) != HAL_OK) {
            printf("spi_sector_erase(%d) failed: %d\r\n", (unsigned int)dest_addr_base, (unsigned int)res);
            return;
        }

        // SOMEHOW WE ARE NOT HANDLING THE LAST BYTES CALCULATION PROPERLY --- SEEMS WE HAVE 1804 bytes should be left at the end
        uint32_t pages_to_write =
            MIN((spi_bytes_remaining + SPI_FLASH_PAGE_SIZE - 1) / SPI_FLASH_PAGE_SIZE, SPI_PAGES_PER_SD_CHUNK);
#ifdef DEBUG_PRINT_COPY
        printf("pages_to_write=%lu\r\n", pages_to_write);
#endif

        for (uint32_t page = 0; page < pages_to_write; page++) {
#ifdef DEBUG_PRINT_COPY
            printf("page=%lu\r\n", page);
#endif
            assert(spi_bytes_remaining > 0);

#ifdef DEBUG_PRINT_COPY
            printf("    spi_bytes_remaining=%lu\r\n", spi_bytes_remaining);
#endif

            // Write the page (or less)
            uint32_t spi_size_to_write = SPI_FLASH_PAGE_SIZE;
            uint32_t dest_addr         = dest_addr_base + (page * SPI_FLASH_PAGE_SIZE);
            uint8_t* chunk_addr        = chunk + (page * SPI_FLASH_PAGE_SIZE);

#ifdef DEBUG_PRINT_COPY
            printf("    dest_addr:  %lu\r\n", dest_addr);
            printf("    chunk_addr: 0x%08lx\r\n", (uint32_t)chunk_addr);
#endif

            assert(dest_addr % SPI_FLASH_PAGE_SIZE == 0);
            assert(spi_size_to_write == SPI_FLASH_PAGE_SIZE);

#ifdef DEBUG_PRINT_COPY
            printf("    spi_size_to_write=%lu\r\n", spi_size_to_write);
            printf("    dest_addr=%lu\r\n", dest_addr);
            printf("    chunk_addr=0x%08lx\r\n", (uint32_t)chunk_addr);
#endif

#ifdef DEBUG_PRINT_SPI_WRITES
            bytes_to_hex_str(chunk_addr, spi_size_to_write, str_buf, 64, "\r\n");
            printf("writing:\r\n%s\r\n", str_buf);
#endif

            if ((res = spi_write(dest_addr, spi_size_to_write, chunk_addr)) != HAL_OK) {
                printf("    spi_write(%d,) failed: %d\r\n", (unsigned int)dest_addr, (unsigned int)res);
                return;
            }

            // Verify that the write was good
            memset(verify_buf, 0, sizeof(verify_buf));
            if ((res = spi_read(dest_addr, spi_size_to_write, verify_buf)) != HAL_OK) {
                printf("    spi_read(%d,) failed: %d\r\n", (unsigned int)dest_addr, (unsigned int)res);
                return;
            }

#ifdef DEBUG_PRINT_SPI_VERIFY_READS
            bytes_to_hex_str(verify_buf, spi_size_to_write, str_buf, 64, "\r\n");
            printf("read back:\r\n%s\r\n", str_buf);
#endif
            if (memcmp(verify_buf, chunk_addr, spi_size_to_write) != 0) {
                // Jump back to the beginning of the block so that we erase the sector before writing again
#ifdef DEBUG_PRINT_VERIFY_ERRORS
                printf("    !!!!! Page at addr 0x%08lx didn't write properly (page=%lu).  Restarting block.\r\n",
                       (uint32_t)dest_addr, page);
                bytes_to_hex_str(verify_buf, spi_size_to_write, str_buf, 64, "\r\n");
                printf("    verify_buf:\r\n%s\r\n", str_buf);
                bytes_to_hex_str(chunk_addr, spi_size_to_write, str_buf, 64, "\r\n");
                printf("    block[page]:\r\n%s\r\n", str_buf);
#endif
                spi_bytes_remaining = spi_bytes_remaining_at_start_of_chunk;
                goto restart_chunk;
            }

#ifdef DEBUG_PRINT_COPY
            printf("   VERIFIED!\r\n");
#endif

            // Refresh the display
            uint8_t percent_done =
                (uint8_t)((float)(total_spi_data_len - spi_bytes_remaining) / (float)total_spi_data_len * 100.0f);
            if (percent_done - last_percent > 2) {
                display_progress_bar(PROGRESS_BAR_MARGIN, PROGRESS_BAR_Y, SCREEN_WIDTH - (PROGRESS_BAR_MARGIN * 2), 0,
                                     percent_done, "Preparing Update...");
                last_percent = percent_done;
            }

            // Successfully written, so move along
            spi_bytes_remaining -= spi_size_to_write;
        }
    }
    display_progress_bar(PROGRESS_BAR_MARGIN, PROGRESS_BAR_Y, SCREEN_WIDTH - (PROGRESS_BAR_MARGIN * 2), 0, 100,
                         "Preparing Update...");

#ifdef DEBUG_PRINT_COPY
    uint8_t spi_hash[HASH_LEN] = {0};
    calculate_spi_hash(hdr, spi_hash, sizeof(spi_hash));
    bytes_to_hex_str(spi_hash, sizeof(spi_hash), str_buf, 64, "\r\n");
    printf(
        "==========================================================================================================================\r\n");
    printf("spi_hash:\r\n%s\r\n", str_buf);
    printf(
        "==========================================================================================================================\r\n\r\n");
#endif
}

#endif /* FACTORY_TEST */
