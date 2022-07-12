// SPDX-FileCopyrightText: 2022 Foundation Devices, Inc.
// <hello@foundationdevices.com> SPDX-License-Identifier: GPL-3.0-or-later
//
// SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
// SPDX-License-Identifier: GPL-3.0-only
//
/*
 * (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
 * and is covered by GPLv3 license found in COPYING.
 */
#pragma once

#include <stdbool.h>

#include "fwheader.h"
#include "secresult.h"

extern secresult verify_header(passport_firmware_header_t* hdr);
extern secresult verify_current_firmware(bool process_led);
extern secresult verify_signature(passport_firmware_header_t* hdr, uint8_t* fw_hash, uint32_t hashlen);
