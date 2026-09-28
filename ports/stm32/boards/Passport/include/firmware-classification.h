// SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
// SPDX-License-Identifier: GPL-3.0-or-later

#pragma once

#include <stdbool.h>
#include "fwheader.h"
#include "firmware-keys.h"

static inline bool firmware_is_user_signed(const passport_firmware_header_t* header) {
    // The first key selects which signature-verification path is used.
    return header->signature.pubkey1 == FW_USER_KEY;
}
