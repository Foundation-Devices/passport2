// SPDX-FileCopyrightText: 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//
// SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
// SPDX-License-Identifier: GPL-3.0-only
//
#include <stdint.h>
#include <string.h>

#ifndef PASSPORT_COSIGN_TOOL
#include "stm32h7xx_hal.h"
#endif /* PASSPORT_COSIGN_TOOL */

#include "fwheader.h"
#include "sha256.h"
#include "utils.h"
#ifndef PASSPORT_COSIGN_TOOL
#include "secrets.h"
#endif
#define UID_LEN (96 / 8) /* 96 bits (Section 61.1 in STMH753 RM) */

void hash_bl(uint8_t* bl, size_t bllen, uint8_t* hash, uint8_t hashlen) {
    SHA256_CTX ctx;

    sha256_init(&ctx);

    /* Checksum the bootloader */
    sha256_update(&ctx, bl, bllen);
    sha256_final(&ctx, hash);

    /* double SHA256 */
    sha256_init(&ctx);
    sha256_update(&ctx, hash, hashlen);
    sha256_final(&ctx, hash);
}

// This hash is used for the integrity check of the firmware and is not user-facing
void hash_fw(fw_info_t* hdr, uint8_t* fw, size_t fwlen, uint8_t* hash, uint8_t hashlen) {
    SHA256_CTX ctx;

    sha256_init(&ctx);

    // Checksum the info block too
    sha256_update(&ctx, (uint8_t*)hdr, sizeof(fw_info_t));

    /* Checksum the firmware */
    sha256_update(&ctx, fw, fwlen);
    sha256_final(&ctx, hash);

    /* double SHA256 */
    sha256_init(&ctx);
    sha256_update(&ctx, hash, hashlen);
    sha256_final(&ctx, hash);
}

// User-facing hash includes signatures so user can compare to downloaded file.
// When exclude_hdr is true, only the code part of the firmware is hashed, which
// would allow a user to build the code themselves and compare the hash with what
// is in the Passport.
void hash_fw_user(uint8_t* fw, size_t fwlen, uint8_t* hash, uint8_t hashlen, bool exclude_hdr) {
    SHA256_CTX ctx;

    // Skip the whole header if requested
    if (exclude_hdr) {
        fw += FW_HEADER_SIZE;
        fwlen -= FW_HEADER_SIZE;
    }

    sha256_init(&ctx);
    sha256_update(&ctx, fw, fwlen);
    sha256_final(&ctx, hash);
}

#ifndef PASSPORT_COSIGN_TOOL
void hash_board(uint8_t* fw_hash, uint8_t fw_hash_len, uint8_t* hash, uint8_t hashlen) {
    SHA256_CTX     ctx;
    FLASH_TypeDef* flash   = (FLASH_TypeDef*)FLASH_R_BASE;
    uint32_t       options = (uint32_t)(flash->OPTSR_CUR & FLASH_OPTSR_RDP_Msk);

    sha256_init(&ctx);
    /* Add in firmware signature */
    sha256_update(&ctx, fw_hash, fw_hash_len);
    /* Add SE serial number */
    sha256_update(&ctx, rom_secrets->se_serial_number, sizeof(rom_secrets->se_serial_number));
    /* Add option bytes */
    sha256_update(&ctx, (uint8_t*)&options, sizeof(uint32_t));
    /* Add unique device ID */
    sha256_update(&ctx, (uint8_t*)UID_BASE, UID_LEN);
    sha256_final(&ctx, hash);

    /* double SHA256 */
    sha256_init(&ctx);
    sha256_update(&ctx, hash, hashlen);
    sha256_final(&ctx, hash);
}

void get_device_hash(uint8_t* hash) {
    SHA256_CTX ctx;
    sha256_init(&ctx);

    /* Add SE serial number */
    sha256_update(&ctx, rom_secrets->se_serial_number, sizeof(rom_secrets->se_serial_number));

    /* One-time pad */
    sha256_update(&ctx, rom_secrets->otp_key, sizeof(rom_secrets->otp_key));

    /* Pairing secret */
    sha256_update(&ctx, rom_secrets->pairing_secret, sizeof(rom_secrets->pairing_secret));

    /* Add unique device ID from MCU */
    sha256_update(&ctx, (uint8_t*)UID_BASE, UID_LEN);
    sha256_final(&ctx, hash);

    /* double SHA256 */
    sha256_init(&ctx);
    sha256_update(&ctx, hash, 32);
    sha256_final(&ctx, hash);
}

bool get_serial_number(char* serial_buf, uint8_t serial_buf_len) {
    uint8_t hash[32];
    if (serial_buf_len < 20) {
        return false;
    }

    get_device_hash(hash);

    // Format as serial number
    bytes_to_hex_str(hash, 8, serial_buf, 2, "-");

    return true;
}

#endif /* PASSPORT_COSIGN_TOOL */
