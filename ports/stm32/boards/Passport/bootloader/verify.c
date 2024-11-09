// SPDX-FileCopyrightText: 2022 Foundation Devices, Inc.
// <hello@foundation.xyz> SPDX-License-Identifier: GPL-3.0-or-later
//
// SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
// SPDX-License-Identifier: GPL-3.0-only
//
/*
 * (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
 * and is covered by GPLv3 license found in COPYING.
 *
 * verify.c -- Check signatures on firmware images in flash.
 *
 */
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

#include "delay.h"
#include "firmware-keys.h"
#include "hash.h"
#include "se-config.h"
#include "se.h"
#include "sha256.h"
#include "uECC.h"
#include "utils.h"

#include "se-atecc608a.h"
#include "verify.h"

#ifdef DEBUG_PRINT_VERIFY
char str_buf[512];
#endif

secresult verify_header(passport_firmware_header_t* hdr) {
#ifdef SCREEN_MODE_COLOR
    if (hdr->info.magic != FW_HEADER_MAGIC_COLOR) goto fail;
#endif
#ifdef SCREEN_MODE_MONO
    if (hdr->info.magic != FW_HEADER_MAGIC) goto fail;
#endif
    if (hdr->info.timestamp == 0) goto fail;
    if (hdr->info.fwversion[0] == 0x0) goto fail;
    if (hdr->info.fwlength < FW_HEADER_SIZE) goto fail;
    if (hdr->info.fwlength > FW_MAX_SIZE) goto fail;

    // if (hdr->signature.pubkey1 == 0) goto fail;
    if ((hdr->signature.pubkey1 != FW_USER_KEY) && (hdr->signature.pubkey1 > FW_MAX_PUB_KEYS)) goto fail;
    if (hdr->signature.pubkey1 != FW_USER_KEY) {
        // if (hdr->signature.pubkey2 == 0) goto fail;
        if (hdr->signature.pubkey2 > FW_MAX_PUB_KEYS) goto fail;
    }

    return SEC_TRUE;

fail:
    return SEC_FALSE;
}

secresult verify_signature(passport_firmware_header_t* hdr, uint8_t* fw_hash, uint32_t hashlen) {
    int rc;

    if (hdr->signature.pubkey1 == FW_USER_KEY) {
        uint8_t user_public_key[72] = {0};
#ifdef DEBUG_PRINT_VERIFY
        printf("Checking user-signed signature\r\n");
#endif
        /*
         * It looks like the user signed this firmware so, in order to
         * validate, we need to get the public key from the SE.
         */
        se_pair_unlock();
        rc = se_read_data_slot(KEYNUM_user_fw_pubkey, user_public_key, sizeof(user_public_key));
#ifdef DEBUG_PRINT_VERIFY
        bytes_to_hex_str(user_public_key, 64, str_buf, 64, "\r\n");
        printf("user pubkey:\r\n%s\r\n", str_buf);
#endif
        if (rc < 0) {
            printf("can't read data slot for pubkey\r\n");
            return SEC_FALSE;
        }

        rc = uECC_verify(user_public_key, fw_hash, hashlen, hdr->signature.signature1, uECC_secp256k1());
        if (rc == 0) {
            printf("Verify failed for user key!\r\n");
            return SEC_FALSE;
        }
#ifdef DEBUG_PRINT_VERIFY
        printf("User-signed firmware signature is VALID!\r\n");
#endif
    } else {
#ifdef DEBUG_PRINT_VERIFY
        printf("Checking officially-signed signature\r\n");
        bytes_to_hex_str(fw_hash, hashlen, str_buf, 64, "\r\n");
        printf("hash:\r\n%s\r\n", str_buf);

        bytes_to_hex_str(hdr->signature.signature1, sizeof(hdr->signature.signature1), str_buf, 64, "\r\n");
        printf("signature1:\r\n%s\r\n", str_buf);

        bytes_to_hex_str(hdr->signature.signature2, sizeof(hdr->signature.signature2), str_buf, 64, "\r\n");
        printf("signature2:\r\n%s\r\n", str_buf);
#endif

        // Ensure the firmware is signed by two different keys and that the keys are in range
        if (hdr->signature.pubkey1 == hdr->signature.pubkey2) {
            printf("pubkeys are the same!\r\n");
            return SEC_FALSE;
        }

        if (hdr->signature.pubkey1 >= FW_MAX_PUB_KEYS || hdr->signature.pubkey2 >= FW_MAX_PUB_KEYS) {
            printf("pubkey index out of range\r\n");
            return SEC_FALSE;
        }

        rc = uECC_verify(approved_pubkeys[hdr->signature.pubkey1], fw_hash, hashlen, hdr->signature.signature1,
                         uECC_secp256k1());
        if (rc == 0) {
            printf("Invalid Signature 1\r\n");
            return SEC_FALSE;
        }

        rc = uECC_verify(approved_pubkeys[hdr->signature.pubkey2], fw_hash, hashlen, hdr->signature.signature2,
                         uECC_secp256k1());
        if (rc == 0) {
            printf("Invalid Signature 2\r\n");
            return SEC_FALSE;
        }
#ifdef DEBUG_PRINT_VERIFY
        printf("Officially-signed firmware signature is VALID!\r\n");
#endif
    }

    return SEC_TRUE;
}

secresult verify_current_firmware(bool process_led) {
    uint8_t                     fw_hash[HASH_LEN];
    passport_firmware_header_t* fwhdr = (passport_firmware_header_t*)FW_HDR;
    uint8_t*                    fwptr = (uint8_t*)fwhdr + FW_HEADER_SIZE;

    if (!verify_header(fwhdr)) return ERR_INVALID_FIRMWARE_HEADER;

    hash_fw(&fwhdr->info, fwptr, fwhdr->info.fwlength, fw_hash, sizeof(fw_hash));

    if (verify_signature(fwhdr, fw_hash, sizeof(fw_hash)) == SEC_FALSE) return ERR_INVALID_FIRMWARE_SIGNATURE;

#ifdef PRODUCTION_BUILD
    if (process_led) {
        uint8_t board_hash[HASH_LEN];
        hash_board(fw_hash, sizeof(fw_hash), board_hash, sizeof(board_hash));

        int rc = se_set_gpio_secure(board_hash);
        if (rc < 0) {
            printf("verify_current_firmware() ERR_FIRMWARE_HASH_DOES_NOT_MATCH_SE!\r\n");
            return ERR_FIRMWARE_HASH_DOES_NOT_MATCH_SE;
        }
    }
#endif /* PRODUCTION_BUILD */

    return SEC_TRUE;
}

// EOF
