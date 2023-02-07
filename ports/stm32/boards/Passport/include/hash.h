// SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//
// SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
// SPDX-License-Identifier: GPL-3.0-only
//
#pragma once

#include <stdbool.h>

#include "fwheader.h"

extern void hash_bl(uint8_t* bl, size_t bllen, uint8_t* sig, uint8_t siglen);
extern void hash_fw(fw_info_t* hdr, uint8_t* fw, size_t fwlen, uint8_t* sig, uint8_t siglen);
extern void hash_fw_user(uint8_t* fw, size_t fwlen, uint8_t* hash, uint8_t hashlen, bool exclude_hdr);
extern void hash_board(uint8_t* fw_signature, uint8_t fw_signature_len, uint8_t* sig, uint8_t siglen);
extern void get_device_hash(uint8_t* hash);
extern bool get_serial_number(char* serial_buf, uint8_t serial_buf_len);
