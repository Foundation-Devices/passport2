/*
 * SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#ifndef _SECRETS_H_
#define _SECRETS_H_

typedef struct __attribute__((packed)) {
    uint8_t pairing_secret[32];
    uint8_t se_serial_number[9];
    uint8_t otp_key[72];            // key for secret encryption (seed storage)
    uint8_t hash_cache_secret[32];  // encryption for cached pin hash value
    uint8_t padding[15];            // to align to a flash word (32 bytes)
} rom_secrets_t;

#define rom_secrets ((rom_secrets_t*)BL_NVROM_BASE)

#endif /* _SECRETS_H_ */
