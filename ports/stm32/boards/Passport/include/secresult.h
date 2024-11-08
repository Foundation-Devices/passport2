// SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundation.xyz>
// SPDX-License-Identifier: GPL-3.0-or-later
//
// secresult.h - Secure return values from security-critical functions -- ensures that single bit glitches cannot
//               cause the wrong code path to be taken.

#pragma once

#include <stdint.h>

// A true/false result with error numbers encoded as alternate values
typedef uint32_t secresult;
#define SEC_TRUE 0xAAAAAAAAU
#define SEC_FALSE 0x00000000U

// Error values
#define ERR_ROM_SECRETS_TOO_BIG 0x50505050U
#define ERR_INVALID_FIRMWARE_HEADER 0x51515151U
#define ERR_INVALID_FIRMWARE_SIGNATURE 0x52525252U
#define ERR_UNABLE_TO_CONFIGURE_SE 0x53535353U
#define ERR_UNABLE_TO_WRITE_ROM_SECRETS 0x54545454U
#define ERR_UNABLE_TO_PROGRAM_FIRMWARE_HASH_IN_SE 0x55555555U
#define ERR_UNABLE_TO_SET_FIRMWARE_TIMESTAMP_IN_SE 0xA3A3A3A3U
#define ERR_FIRMWARE_HASH_DOES_NOT_MATCH_SE 0x56565656U
