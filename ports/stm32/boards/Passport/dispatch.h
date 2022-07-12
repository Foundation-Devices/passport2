// SPDX-FileCopyrightText: 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//
// SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
// SPDX-License-Identifier: GPL-3.0-only
//
/*
 * (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
 * and is covered by GPLv3 license found in COPYING.
 */
#pragma once

// Start DFU, or return doing nothing if chip is secure (no DFU possible).
extern void dfu_by_request(void);

/* Temporary declaration for unit-testing */
extern int se_dispatch(
    int method_num, uint8_t* buf_io, int len_in, uint32_t arg2, uint32_t incoming_sp, uint32_t incoming_lr);

#define CMD_IS_BRICKED 5
#define CMD_READ_SE_SLOT 15
#define CMD_GET_ANTI_PHISHING_WORDS 16
#define CMD_GET_RANDOM_BYTES 17
#define CMD_PIN_CONTROL 18
#define CMD_GET_SE_CONFIG 20
#define CMD_GET_SUPPLY_CHAIN_VALIDATION_WORDS 21

// Subcommands for CMD_PIN_CONTROL
#define PIN_SETUP 0
#define PIN_ATTEMPT 1
#define PIN_CHANGE 2
#define PIN_GET_SECRET 3
