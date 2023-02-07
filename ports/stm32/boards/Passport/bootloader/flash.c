// SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//
// SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
// SPDX-License-Identifier: GPL-3.0-only
//
// (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
// and is covered by GPLv3 license found in COPYING.
//
//
// flash.c -- manage flash and its sensitive contents.
//

#include <errno.h>
#include <string.h>

#include "flash.h"
#include "fwheader.h"
#include "hash.h"
#include "pprng.h"
#include "se-atecc608a.h"
#include "se.h"
#include "utils.h"
#include "verify.h"

const uint32_t num_pages_locked = ((BL_FLASH_SIZE + BL_NVROM_SIZE) / 0x800) - 1;  // == 15

static inline bool is_pairing_secret_programmed(uint8_t* secret, size_t len) {
    uint8_t* ptr = secret;

    for (; len; len--, ptr++) {
        if (*ptr != 0xff) return true;
    }
    return false;
}

static inline secresult is_se_programmed(void) {
    int     rc;
    uint8_t config[128] = {0};

    rc = se_config_read(config);
    if (rc < 0) LOCKUP_FOREVER(); /* Can't talk to the SE */

    if ((config[86] != 0x55) && (config[87] != 0x55)) return SEC_TRUE;
    return SEC_FALSE;
}

// See FLASH_WaitForLastOperation((uint32_t)FLASH_TIMEOUT_VALUE)
// Absolutely MUST be in RAM.
//
__attribute__((section(".ramfunc"))) static inline uint32_t _flash_wait_done(uint32_t bank) {
    uint32_t bsyflag, errorflag;

    if (bank == FLASH_BANK_1)
        bsyflag = FLASH_FLAG_QW_BANK1;
    else
        bsyflag = FLASH_FLAG_QW_BANK2;

    while (__HAL_FLASH_GET_FLAG(bsyflag)) {
        // busy wait
    }

    /* Get Error Flags */
    if (bank == FLASH_BANK_1)
        errorflag = FLASH->SR1 & FLASH_FLAG_ALL_ERRORS_BANK1;
    else
        errorflag = (FLASH->SR2 & FLASH_FLAG_ALL_ERRORS_BANK2) | 0x80000000U;

    /* In case of error reported in Flash SR1 or SR2 register */
    if ((errorflag & 0x7FFFFFFFU) != 0U) {
        /* Clear error programming flags */
        __HAL_FLASH_CLEAR_FLAG(errorflag);

        return errorflag;
    }

    /* Check FLASH End of programming flag  */
    if (bank == FLASH_BANK_1) {
        if (__HAL_FLASH_GET_FLAG_BANK1(FLASH_FLAG_EOP_BANK1)) {
            /* Clear FLASH End of programming flag */
            __HAL_FLASH_CLEAR_FLAG_BANK1(FLASH_FLAG_EOP_BANK1);
        }
    } else {
        if (__HAL_FLASH_GET_FLAG_BANK2(FLASH_FLAG_EOP_BANK2)) {
            /* Clear FLASH End of programming flag */
            __HAL_FLASH_CLEAR_FLAG_BANK2(FLASH_FLAG_EOP_BANK2);
        }
    }

    return 0;
}

__attribute__((section(".ramfunc"))) void flash_lock(void) {
    // see HAL_FLASH_Lock();
    SET_BIT(FLASH->CR1, FLASH_CR_LOCK);
    if (READ_BIT(FLASH->CR1, FLASH_CR_LOCK)) {
        return;
    }
    SET_BIT(FLASH->CR2, FLASH_CR_LOCK);
    if (READ_BIT(FLASH->CR2, FLASH_CR_LOCK)) {
        return;
    }
}

__attribute__((section(".ramfunc"))) void flash_unlock(void) {
    // see HAL_FLASH_Unlock()
    if (READ_BIT(FLASH->CR1, FLASH_CR_LOCK)) {
        /* Authorize the FLASH Bank1 Registers access */
        WRITE_REG(FLASH->KEYR1, FLASH_KEY1);
        WRITE_REG(FLASH->KEYR1, FLASH_KEY2);

        if (READ_BIT(FLASH->CR1, FLASH_CR_LOCK)) {
            return;
        }
    }
    if (READ_BIT(FLASH->CR2, FLASH_CR_LOCK)) {
        /* Authorize the FLASH Bank2 Registers access */
        WRITE_REG(FLASH->KEYR2, FLASH_KEY1);
        WRITE_REG(FLASH->KEYR2, FLASH_KEY2);

        if (READ_BIT(FLASH->CR2, FLASH_CR_LOCK)) {
            return;
        }
    }
}

__attribute__((section(".ramfunc"))) int flash_ob_lock(bool lock) {
    if (!lock) {
        /* see HAL_FLASH_OB_Unlock() */
        if (READ_BIT(FLASH->OPTCR, FLASH_OPTCR_OPTLOCK) != 0U) {
            /* Authorizes the Option Byte registers programming */
            WRITE_REG(FLASH->OPTKEYR, FLASH_OPT_KEY1);
            WRITE_REG(FLASH->OPTKEYR, FLASH_OPT_KEY2);

            /* Verify that the Option Bytes are unlocked */
            if (READ_BIT(FLASH->OPTCR, FLASH_OPTCR_OPTLOCK) != 0U) {
                return -1;
            }
        }
    } else {
        /* see HAL_FLASH_OB_Lock() */
        /* Set the OPTLOCK Bit to lock the FLASH Option Byte Registers access */
        SET_BIT(FLASH->OPTCR, FLASH_OPTCR_OPTLOCK);

        /* Verify that the Option Bytes are locked */
        if (READ_BIT(FLASH->OPTCR, FLASH_OPTCR_OPTLOCK) == 0U) {
            return -1;
        }
    }
    return 0;
}

// See HAL_FLASH_Program(FLASH_TYPEPROGRAM_DOUBLEWORD, ...)
//
// NOTES:
//  - this function **AND** everything it calls, must be in RAM
//  - interrupts are already off here (entire bootloader)
//  - return non-zero on failure; don't try to handle anything
//
__attribute__((section(".ramfunc"))) int flash_burn(uint32_t flash_address, uint32_t data_address) {
    uint32_t       bank;
    uint32_t       rv;
    __IO uint32_t* dest_addr = (__IO uint32_t*)flash_address;
    __IO uint32_t* src_addr  = (__IO uint32_t*)data_address;
    uint8_t        row_index = FLASH_NB_32BITWORD_IN_FLASHWORD;

    if (IS_FLASH_PROGRAM_ADDRESS_BANK1(flash_address))
        bank = FLASH_BANK_1;
    else if (IS_FLASH_PROGRAM_ADDRESS_BANK2(flash_address))
        bank = FLASH_BANK_2;
    else
        return -1;

    _flash_wait_done(bank);

    /* Set PG bit */
    if (bank == FLASH_BANK_1)
        SET_BIT(FLASH->CR1, FLASH_CR_PG);
    else
        SET_BIT(FLASH->CR2, FLASH_CR_PG);

    __ISB();
    __DSB();

    /* Program the 256 bits flash word */
    do {
        *dest_addr = *src_addr;
        dest_addr++;
        src_addr++;
        row_index--;
    } while (row_index != 0U);

    __ISB();
    __DSB();

    rv = _flash_wait_done(bank);

    /* If the program operation is completed, disable the PG*/
    if (bank == FLASH_BANK_1)
        CLEAR_BIT(FLASH->CR1, FLASH_CR_PG);
    else
        CLEAR_BIT(FLASH->CR2, FLASH_CR_PG);

    return rv;
}

// See HAL_FLASHEx_Erase(FLASH_EraseInitTypeDef *pEraseInit, uint32_t *PageError)
//
__attribute__((section(".ramfunc"))) int flash_sector_erase(uint32_t address) {
    uint32_t sector;

    if (IS_FLASH_PROGRAM_ADDRESS_BANK1(address)) {
        sector = (address - FLASH_BANK1_BASE) / FLASH_SECTOR_SIZE;

        /* Protect against erasing sector 0 (contains the bootloader) */
        if (sector == 0) return -1;

        _flash_wait_done(FLASH_BANK_1);

        /* reset Program/erase VoltageRange for Bank1 */
        FLASH->CR1 &= ~(FLASH_CR_PSIZE | FLASH_CR_SNB);
        FLASH->CR1 |= (FLASH_CR_SER | FLASH_VOLTAGE_RANGE_3 | (sector << FLASH_CR_SNB_Pos));
        FLASH->CR1 |= FLASH_CR_START;

        _flash_wait_done(FLASH_BANK_1);

        /* The erase operation is completed, disable the SER Bit */
        FLASH->CR1 &= (~(FLASH_CR_SER | FLASH_CR_SNB));
    } else if (IS_FLASH_PROGRAM_ADDRESS_BANK2(address)) {
        sector = (address - FLASH_BANK2_BASE) / FLASH_SECTOR_SIZE;

        _flash_wait_done(FLASH_BANK_2);

        /* reset Program/erase VoltageRange for Bank2 */
        FLASH->CR2 &= ~(FLASH_CR_PSIZE | FLASH_CR_SNB);
        FLASH->CR2 |= (FLASH_CR_SER | FLASH_VOLTAGE_RANGE_3 | (sector << FLASH_CR_SNB_Pos));
        FLASH->CR2 |= FLASH_CR_START;

        _flash_wait_done(FLASH_BANK_2);

        /* The erase operation is completed, disable the SER Bit */
        FLASH->CR2 &= (~(FLASH_CR_SER | FLASH_CR_SNB));
    } else
        return -1;

    return 0;
}

#define JUST_PROGRAM_ROM_SECRETS
#ifdef JUST_PROGRAM_ROM_SECRETS
__attribute__((section(".ramfunc"))) static int flash_rom_secrets(rom_secrets_t* secrets) {
    __IO uint32_t* src_secrets                            = (__IO uint32_t*)secrets;
    __IO uint32_t* flash_secrets                          = (__IO uint32_t*)(BL_NVROM_BASE);
    __IO uint32_t  empty[FLASH_NB_32BITWORD_IN_FLASHWORD] = {0};

    uint32_t flash_word_len = sizeof(uint32_t) * FLASH_NB_32BITWORD_IN_FLASHWORD;
    uint32_t pos            = (uint32_t)src_secrets;
    uint32_t dest           = (uint32_t)flash_secrets;
    uint32_t zeros          = (uint32_t)empty;
    int      i;

    flash_unlock();

    for (i = 0; i < sizeof(rom_secrets_t); i += flash_word_len, pos += flash_word_len, dest += flash_word_len) {
        if (flash_burn(dest, pos)) return -1;
    }

    for (; i < BL_NVROM_SIZE; i += flash_word_len, dest += flash_word_len) {
        if (flash_burn(dest, zeros)) return -1;
    }

    flash_lock();
    return 0;
}
#else
__attribute__((section(".ramfunc"))) static int flash_bootloader(rom_secrets_t* secrets) {
    __IO uint32_t* sector0         = (__IO uint32_t*)BL_FLASH_BASE;
    __IO uint32_t* sector0_end     = (__IO uint32_t*)(BL_FLASH_BASE + BL_FLASH_SIZE);
    __IO uint32_t* sram            = (__IO uint32_t*)D1_AXISRAM_BASE;
    __IO uint32_t* src_secrets     = (__IO uint32_t*)secrets;
    __IO uint32_t* src_secrets_end = (__IO uint32_t*)((uint32_t)secrets + sizeof(rom_secrets_t));
    __IO uint32_t* sram_secrets    = (__IO uint32_t*)(D1_AXISRAM_BASE + BL_FLASH_SIZE - BL_NVROM_SIZE);

    uint32_t flash_word_len = sizeof(uint32_t) * FLASH_NB_32BITWORD_IN_FLASHWORD;
    uint32_t pos            = (uint32_t)sram;
    uint32_t dest           = (uint32_t)sector0;
    int      i;

    /* Copy sector 0 to SRAM */
    while (sector0 < sector0_end) {
        *sram = *sector0;
        ++sram;
        ++sector0;
    }

    /* Copy the ROM secrets to SRAM */
    while (src_secrets < src_secrets_end) {
        *sram_secrets = *src_secrets;
        ++sram_secrets;
        ++src_secrets;
    }

    flash_unlock();

    for (i = 0; i < BL_FLASH_SIZE; i += flash_word_len, pos += flash_word_len, dest += flash_word_len) {
        if (flash_burn(dest, pos)) {
            return -1;
        }
    }

    flash_lock();
    return 0;
}
#endif /* JUST_PROGRAM_ROM_SECRETS */

__attribute__((section(".ramfunc"))) void flash_lockdown_hard(void) {
#ifdef LOCKED
    _flash_wait_done(FLASH_BANK_1);
    _flash_wait_done(FLASH_BANK_2);
    flash_ob_lock(false);

    MODIFY_REG(FLASH->OPTSR_PRG, FLASH_OPTSR_RDP, (uint32_t)OB_RDP_LEVEL_2);

    _flash_wait_done(FLASH_BANK_1);
    _flash_wait_done(FLASH_BANK_2);
    SET_BIT(FLASH->OPTCR, FLASH_OPTCR_OPTSTART);

    flash_ob_lock(true);
#endif /* LOCKED */
}

static void pick_pairing_secret(rom_secrets_t* local) {
    uint32_t  secret[8];
    int       i;
    uint32_t* pos;
    uint16_t  len;

    for (i = 0; i < 8; i++) {
        secret[i] = rng_sample();
    }

    // enforce policy that first word is not all ones (so it never
    // looks like unprogrammed flash).
    while (secret[0] == 0xff) {
        secret[0] = rng_sample();
    }

    memcpy(local->pairing_secret, secret, sizeof(secret));

    pos = (uint32_t*)local->otp_key;
    len = sizeof(local->otp_key);
    for (i = 0; i < len; i += sizeof(uint32_t), ++pos) {
        *pos = rng_sample();
    }

    pos = (uint32_t*)&local->hash_cache_secret;
    len = sizeof(local->hash_cache_secret);
    for (i = 0; i < len; i += sizeof(uint32_t), ++pos) {
        *pos = rng_sample();
    }
}

secresult flash_first_boot(void) {
    int                         rc;
    uint8_t                     fw_hash[HASH_LEN]    = {0};
    uint8_t                     board_hash[HASH_LEN] = {0};
    uint8_t                     zeros[HASH_LEN]      = {0};
    passport_firmware_header_t* fwhdr                = (passport_firmware_header_t*)FW_HDR;
    uint8_t*                    fwptr                = (uint8_t*)fwhdr + FW_HEADER_SIZE;
    bool                        secrets_already_programmed;

    rom_secrets_t local_secrets = {0};

    if (sizeof(rom_secrets_t) > 2048) return ERR_ROM_SECRETS_TOO_BIG;

    if (verify_header(fwhdr) != SEC_TRUE) return ERR_INVALID_FIRMWARE_HEADER;

    hash_fw(&fwhdr->info, fwptr, fwhdr->info.fwlength, fw_hash, sizeof(fw_hash));

    if (verify_signature(fwhdr, fw_hash, sizeof(fw_hash)) == SEC_FALSE) return ERR_INVALID_FIRMWARE_SIGNATURE;

    secrets_already_programmed =
        is_pairing_secret_programmed(rom_secrets->pairing_secret, sizeof(rom_secrets->pairing_secret));

    if (secrets_already_programmed)
        memcpy(&local_secrets, rom_secrets, sizeof(local_secrets));
    else
        pick_pairing_secret(&local_secrets);

    rc = se_setup_config(&local_secrets);
    if (rc != 0) return ERR_UNABLE_TO_CONFIGURE_SE;

    if (!secrets_already_programmed) {
        HAL_SuspendTick();
#ifdef JUST_PROGRAM_ROM_SECRETS
        rc = flash_rom_secrets(&local_secrets);
#else
        rc = flash_bootloader(&local_secrets);
#endif /* JUST_PROGRAM_ROM_SECRETS */
        HAL_ResumeTick();
        if (rc < 0) return ERR_UNABLE_TO_WRITE_ROM_SECRETS;
    }

#ifdef LOCKED
    // We need to lockdown the flash BEFORE programming the first board_hash into the SE so that the correct
    // option bytes from the MCU are included in the hash.
    flash_lockdown_hard();
#endif

#ifdef PRODUCTION_BUILD
    hash_board(fw_hash, sizeof(fw_hash), board_hash, sizeof(board_hash));
#else
    memset(board_hash, 0, sizeof(board_hash));
#endif /* PRODUCTION_BUILD */

    // Program the first board hash
    rc = se_program_board_hash(zeros, board_hash);
    if (rc < 0) return ERR_UNABLE_TO_PROGRAM_FIRMWARE_HASH_IN_SE;

    // Set the matching firmware timestamp
    rc = se_set_firmware_timestamp(board_hash, fwhdr->info.timestamp);
    if (rc < 0) return ERR_UNABLE_TO_SET_FIRMWARE_TIMESTAMP_IN_SE;

    return SEC_TRUE;
}

secresult flash_is_programmed(void) {
    if (!is_pairing_secret_programmed(rom_secrets->pairing_secret, sizeof(rom_secrets->pairing_secret)))
        return SEC_FALSE;

    return is_se_programmed();
}

#ifdef LOCKED
secresult flash_is_locked(void) {
    uint32_t rdp_level = READ_BIT(FLASH->OPTSR_CUR, FLASH_OPTSR_RDP);
    if (rdp_level == OB_RDP_LEVEL_2) return SEC_TRUE;
    return SEC_FALSE;
}
#endif /* LOCKED */
